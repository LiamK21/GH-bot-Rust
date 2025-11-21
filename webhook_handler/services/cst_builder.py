import difflib
import logging
import re
from typing import cast

from tree_sitter import Language, Node, Parser, Tree

from webhook_handler.helper import git_diff
from webhook_handler.services.pr_diff_context import PullRequestDiffContext

logger = logging.getLogger(__name__)


class CSTBuilder:
    def __init__(self, language: Language, pr_diff_ctx: PullRequestDiffContext) -> None:
        self._parser = Parser(language)
        self._pr_diff_ctx = pr_diff_ctx

    def _parse(self, source_code: str) -> Tree:
        try:
            return self._parser.parse(bytes(source_code, "utf8"))
        except SyntaxError:
            raise ValueError("Failed to parse source code")


    def append_test(self, file_content: str, new_test: str, imports: list[str]) -> str:
        """
        Insert new_test at the bottom of the file_content inside the 'mod tests' module.
        If no such module exists, it is created at the end of the file_content.

        Parameters:
            file_content (str): The file content where the function will be inserted
            new_test (str): The new function to be inserted

        Returns:
            str: The new file content with the inserted function
        """

        tree = self._parse(file_content)

        if tree is not None:
            mod_test_item: Node | None = self._get_mod_test_node(tree.root_node)

            if not mod_test_item:
                test_block = self._create_test_block(new_test, imports)
                return "\n".join([file_content, test_block])

            # if a mod tests already exists, walk it
            declaration_list = next(
                (
                    child
                    for child in mod_test_item.named_children
                    if child.type == "declaration_list"
                ),
                None,
            )
            assert (
                declaration_list is not None
            ), "Expected a declaration_list in the mod tests module, no mod block exists!"
            
            i = self._remove_duplicate_imports(declaration_list, imports)
            
            last_function_item: Node | None = None
            for child in declaration_list.named_children[i:]:
                if child.type == "function_item":
                    last_function_item = child

            if not last_function_item:
                raise ValueError(f"No function defined")

                # determine indentation
            last_func_line = last_function_item.start_point[
                0
            ]  # line before the last block
            last_code_line = (
                last_function_item.end_point[0] + 1
            )  # last code line of the above block

            # extract indentation
            lines = file_content.splitlines()
            import_point = declaration_list.named_children[i - 1]
            if import_point.type == "function_item":
                last_import_line = import_point.start_point[0]
            else:
                last_import_line = declaration_list.named_children[i - 1].end_point[0]
            import_indentation = len(lines[last_import_line]) - len(
                lines[last_import_line].lstrip()
            )

            indented_new_imports = (
                "\n".join(
                    " " * import_indentation + line if line.strip() else ""
                    for line in imports
                )
                + "\n"
            )
            last_func_line_content = lines[last_func_line]
            func_indentation = len(last_func_line_content) - len(
                last_func_line_content.lstrip()
            )

            # add the new function
            indented_new_function = "\n".join(
                " " * func_indentation + line if line.strip() else ""
                for line in new_test.splitlines()
            )

            updated_lines = (
                lines[:last_import_line]
                + [indented_new_imports]
                + lines[last_import_line:last_code_line]
                + ["\n" + indented_new_function]
                + lines[last_code_line:]
            )
            return "\n".join(updated_lines)

        return ""

    def _create_test_block(self, new_test: str, imports: list[str]) -> str:
        use_declarations: str = "\n".join(
            "" * 4 + imp.strip() for imp in imports if imp.strip()
        )
        test_block = (
            "#[cfg(test)]\n"
            "mod tests {\n"
            f"{use_declarations}\n\n"
            f"{new_test}\n"
            "}\n"
        )
        return test_block

    def _get_mod_test_node(self, node: Node) -> Node | None:
        """Extract the tests module of a rust file"""
        passed_children = 0
        for child in node.named_children:
            if (
                child.type == "mod_item" and
                (self._get_node_name(child).strip() == "test" or
                 self._get_node_name(child).strip() == "tests"
                )
            ):
                return child
            passed_children += 1

        return None


    def _remove_duplicate_imports(self, declaration_list: Node, imports: list[str]) -> int:
        """
        Scan file for existing imports and remove any duplicate imports that are provided by the model
        
        Parameters:
            declaration_list (Node): The 'mod tests' block node to scan for existing imports
            imports (list): The list of imports from the model to check for duplicates
        
        Returns:
            int: The index of the first non-import child (+1) in the declaration_list
        """
        def _transform_group_import_into_single_imports(group_import: str) -> list[str]:
            root = group_import.strip()[: group_import.index("{")]
            items = group_import[group_import.index("{") + 1 : group_import.index("}")]
            split = items.split(",")
            return [root + item.strip() + ";" for item in split if item.strip()]
        
        
        i = 0
        while i < len(declaration_list.named_children):
            curr_child = declaration_list.named_children[i]
            i += 1
            child_type = curr_child.type
            # Assumption: All imports are at the top of the mod tests block
            # import statements
            if child_type == "use_declaration":
                pass
            # check that there are no collisions with extern crate declarations
            elif child_type == "extern_crate_declaration":
                crate_declaration = cast(bytes, curr_child.text).decode("utf-8").strip()
                crate_name = crate_declaration.replace("extern crate", "").rstrip(";").strip()
                for imp in imports:
                    imp_list = imp.removeprefix("use ").removesuffix(";").strip().split("::")
                    if crate_name in imp_list[-1]:
                        imports.remove(imp)
                continue
            else:
                break

            existing_import = cast(bytes, curr_child.text).decode("utf-8").strip()
            
            # Handle group imports
            if existing_import.__contains__("{") and existing_import.__contains__("}"):
                existing_imports = _transform_group_import_into_single_imports(existing_import)
                for existing_import in existing_imports:
                    self._handle_single_imports(existing_import, imports)
                continue
            
            self._handle_single_imports(existing_import, imports)
            
        return i
    
    def _handle_single_imports(self, existing_import: str, imports: list[str]) -> None:
        """
        Remove any single import from the imports list that is already present,
        either as an exact match, as part of a glob import, or colliding with an existing import.
        
        Parameters:
            existing_import (str): The existing import statement to check against
            imports (list): The list of imports from the model to check for duplicates
        """
        existing_import_list = existing_import.removeprefix("use ").removesuffix(";").split("::")
        
        imp_idx = 0
        while imp_idx < len(imports):
            imp = imports[imp_idx]
            imp_list = imp.strip().removeprefix("use ").removesuffix(";").split("::")
            
            # Remove directly matching imports    
            if imp_list == existing_import_list:
                imports.remove(imp)
                continue
            
            # Remove imports that are covered by a glob import
            elif existing_import_list[-1] == "*":
                if len(imp_list) >= len(existing_import_list):
                    same_crate: bool = True
                    for j in range(len(existing_import_list) - 1):
                        if imp_list[j] != existing_import_list[j]:
                            same_crate = False
                            break
                    if same_crate:
                        imports.remove(imp)
                        continue
            
            # Remove imports that collide with an existing import
            # Assumption: If the last part of the import is the same, 
            #             it is assumed that the model import is false
            elif existing_import_list[-1] == imp_list[-1]:
                imports.remove(imp)
                continue
            
            imp_idx += 1

    @staticmethod
    def _get_node_name(node: Node, fallback: str = "") -> str:
        """
        Return the name of a node (i.e., function / class name).

        Parameters:
            node (Node): The node to get the name of
            fallback (str, optional): The fallback name to return

        Returns:
            str: The name of the node
        """

        identifier = node.child_by_field_name("name")
        return identifier.text.decode("utf-8") if identifier else fallback
