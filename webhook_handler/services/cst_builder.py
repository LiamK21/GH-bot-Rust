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

    # def get_sliced_code_files(self):
    #     """
    #     Detects which files have been modified to call slice_javascript_code.

    #     Returns:
    #         list: Sliced code for modified code, unsliced for untouched code.
    #     """

    #     if not self._pr_diff_ctx.code_names:
    #         return self._pr_diff_ctx.code_before

    #     print("--- Golden Code Patch ---")
    #     print(self._pr_diff_ctx.golden_code_patch)

    #     code_after, stderr = git_diff.apply_patch(
    #         self._pr_diff_ctx.code_before, self._pr_diff_ctx.golden_code_patch
    #     )

    #     patches = [
    #         "diff --git" + x
    #         for x in self._pr_diff_ctx.golden_code_patch.split("diff --git")[1:]
    #     ]
    #     result = []

    #     for before, after, diff in zip(
    #         self._pr_diff_ctx.code_before, code_after, patches
    #     ):
    #         # before_map is lines removed, after_map is lines added
    #         before_map, after_map = self._build_changed_lines_scope_map(
    #             before, after, diff
    #         )
    #         # print("--- Before Map ---")
    #         # print(before_map)
    #         # if no changes, keep original code
    #         if not before_map and not after_map:
    #             result.append(before)
    #             continue

    #         funcs_before = [list(x.values())[0] for x in before_map]
    #         # print("--- funcs before ---")
    #         # print(funcs_before)
    #         funcs_after = [list(x.values())[0] for x in after_map]

    #         map_cls = self._build_function_class_maps(
    #             funcs_before
    #         ) + self._build_function_class_maps(funcs_after)

    #         # print("--- Function-Class Maps ---")
    #         # print(map_cls)

    #         class2methods = {}
    #         for m2c in map_cls:
    #             for k, v in m2c.items():
    #                 class2methods[v] = class2methods.get(v, []) + [k]

    #         global_funcs = class2methods.pop("global", [])

    #         sliced = self._slice_rust_code(before, global_funcs, class2methods)
    #         # print("--- Sliced Code ---")
    #         # print(sliced)
    #         result.append(sliced)
    #     return result

    def extract_changed_tests(self, pr_file_diff) -> list[str]:
        """
        Analyzes the file for both pre- and post-PR, determines the changed tests and extracts their function names

        Parameters:
            pr_file_diff (PullRequestFileDiff): The file diff including the file name and content of pre- and post-PR

        Returns:
            list: All function names of changed tests
        """
        tests_old = self._extract_test_fname(self._parse(pr_file_diff.before))
        tests_new = self._extract_test_fname(self._parse(pr_file_diff.after))

        if tests_new:
            if tests_old:
                contributing_tests = self._find_changed_tests(tests_old, tests_new)
            else:
                contributing_tests = list(tests_new.keys())
            return contributing_tests

        return []

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
            # Check if there need to be imports added
            i = 0
            while i < len(declaration_list.named_children):
                curr_child = declaration_list.named_children[i]
                i += 1
                child_type = curr_child.type
                # Assumption: All imports are at the top of the mod tests block
                if child_type != "use_declaration":
                    break

                curr_import = cast(bytes, curr_child.text).decode("utf-8").strip()
                # Remove directly matching imports
                if curr_import in imports:
                    imports.remove(curr_import)

                # Remove imports that are covered by a glob import
                elif curr_import == "use super::*;":
                    for imp in imports:
                        if imp.startswith("use super::"):
                            imports.remove(imp)

                # Check if the current import contains an import as part of a group import
                # Note that the other way around is not checked
                # e.g., check if 'use std::path::Path;' is part of 'use std::path::{Path, PathBuf};'
                else:
                    # [std, path, {Path, PathBuf}]
                    curr_import_list = (
                        curr_import.lstrip("use ").rstrip(";").split("::")
                    )
                    for imp in imports:
                        # [std, path, Path]
                        imp_list = imp.lstrip("use ").rstrip(";").split("::")
                        if len(imp_list) == len(curr_import_list):
                            same_crate: bool = True
                            for j in range(len(imp_list) - 1):
                                if imp_list[j] != curr_import_list[j]:
                                    same_crate = False
                                    break
                            if same_crate:
                                import_in_curr_import = curr_import_list[
                                    -1
                                ].__contains__(imp_list[-1])
                                if import_in_curr_import:
                                    imports.remove(imp)

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
                child.type == "mod_item"
                and self._get_node_name(child).strip() == "tests"
            ):
                return child
            passed_children += 1

        return None

    @staticmethod
    def _get_added_removed_lines(
        diff: str,
    ) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
        """
        Analyzes diff to extract which lines have been changed.

        Parameters:
            diff (str): The diff to analyze

        Returns:
            list: Added lines
            list: Removed lines
        """

        added: list[tuple[int, str]] = []
        removed: list[tuple[int, str]] = []

        hunk_header_regex = re.compile(
            r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@"
        )  # matches "@@ -10,7 +10,8 @@", but captures only 10 and 8
        diff_lines = diff.splitlines()
        i = 0

        while i < len(diff_lines):
            line = diff_lines[i]
            match = hunk_header_regex.match(line)
            if match:
                # start lines
                old_start = int(match.group(1))  # first group: original file start line
                new_start = int(match.group(2))  # second group: new file start line

                # line counters
                current_line_original = old_start - 1
                current_line_updated = new_start - 1
                i += 1

                while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
                    patch_line = diff_lines[i]

                    # lines that begin with '+' but not "+++" are added lines
                    if patch_line.startswith("+") and not patch_line.startswith("+++"):
                        current_line_updated += 1
                        added_text = patch_line[1:]  # remove leading '+'
                        added.append((current_line_updated, added_text))

                    # lines that begin with '-' but not "---" are removed lines
                    elif patch_line.startswith("-") and not patch_line.startswith(
                        "---"
                    ):
                        current_line_original += 1
                        removed_text = patch_line[1:]  # remove leading '-'
                        removed.append((current_line_original, removed_text))

                    else:
                        # skip other lines
                        current_line_original += 1
                        current_line_updated += 1

                    i += 1
            else:
                i += 1

        return added, removed

    # def _slice_rust_code(
    #     self, source_code: str, global_funcs: list[str], class2methods: dict
    # ) -> str:
    #     """
    #     Returns a 'sliced' version of the given source code, preserving
    #     original whitespace (and optionally annotating lines with original line numbers).

    #     The resulting code includes:
    #         1. All global variables (including import statements).
    #         2. Global functions whose names are in `global_funcs`.
    #         3. Classes (defined in the global scope) whose names are keys in `class_methods`.
    #             For each kept class:
    #                 - Keep all class-level assignments (properties).
    #                 - Keep the constructor (constructor()) if defined.
    #                 - Keep only the methods listed in class_methods[class_name].
    #                 - Keep JSDocs (which appear outside of class).
    #                 - Keep nested classes

    #     Parameters:
    #         source_code (str): The source code to slice
    #         global_funcs (list): The functions with a 'global' scope
    #         class2methods (dict): Holds which methods belong to a class

    #     Returns:
    #         str: The sliced source code
    #     """

    #     tree = self._parse(source_code)
    #     lines_to_skip: set[int] = set()
    #     source_lines = source_code.splitlines(keepends=True)

    #     def _is_jsdoc(node: Node) -> bool:
    #         return node.type == "comment" and node.text.decode("utf-8").startswith(
    #             "/**"
    #         )

    #     def _skip_lines(start: int, end: int) -> None:
    #         for ln in range(start, end + 1):
    #             lines_to_skip.add(ln)

    #     def _keep_lines(start: int, end: int) -> None:
    #         lines_to_skip.difference_update(list(range(start, end + 1)))

    #     def _keep_top_level_node(node: Node) -> bool:
    #         # print(f"Top-level node type: {node.type}")
    #         if node.type == "mod_item":
    #             return True
    #         if node.type == "function_item":
    #             return True
    #         if node.type == "attribute_item":
    #             return True
    #         if node.type in {"variable_declaration", "lexical_declaration"}:
    #             return True
    #         if node.type == "use_declaration":
    #             return self._get_node_name(node) in global_funcs
    #         if node.type == "class_declaration":
    #             return self._get_node_name(node) in class2methods
    #         if node.type == "comment":
    #             return not _is_jsdoc(node)
    #         return False

    #     def _keep_class_child(node: Node, class_name: str) -> bool:
    #         if node.type in {
    #             "variable_declaration",
    #             "lexical_declaration",
    #             "field_definition",
    #         }:
    #             return True
    #         if node.type == "comment":
    #             return not _is_jsdoc(node)
    #         if node.type == "method_definition":
    #             if self._get_node_name(node) == "constructor":
    #                 return True
    #             allowed_list = [
    #                 method_name.split(".") for method_name in class2methods[class_name]
    #             ]
    #             if any(
    #                 self._get_node_name(node) in sublist for sublist in allowed_list
    #             ):
    #                 return True
    #         return False

    #     def _handle_decorators(node: Node) -> None:
    #         prev = node.prev_sibling
    #         if prev:
    #             txt = prev.text.decode("utf-8")
    #             if all(
    #                 [
    #                     (txt.startswith("@") or txt.startswith("/**")),
    #                     node.start_point[0] - 1 == prev.end_point[0],
    #                 ]
    #             ):
    #                 _mark_lines(prev, True)
    #                 _handle_decorators(prev)

    #     def _mark_lines(node: Node, keep: bool) -> None:
    #         if any(
    #             [
    #                 node.start_point is None,
    #                 node.end_point is None,
    #                 node.start_point[0] is None,
    #                 node.end_point[0] is None,
    #             ]
    #         ):
    #             return

    #         start_line = node.start_point[0] + 1
    #         end_line = node.end_point[0] + 1
    #         if keep:
    #             _keep_lines(start_line, end_line)
    #         else:
    #             _skip_lines(start_line, end_line)
    #             return

    #         if node.type in {
    #             "mod_item",
    #             "function_item",
    #             "method_definition",
    #         }:
    #             _handle_decorators(node)
    #         if node.type == "mod_item":
    #             for child in self._get_node_body(node):
    #                 child_keep = _keep_class_child(child, self._get_node_name(node))
    #                 _mark_lines(child, child_keep)

    #     if tree is not None:
    #         for root_child in tree.root_node.children:
    #             keep_flag = _keep_top_level_node(root_child)
    #             _mark_lines(root_child, keep_flag)

    #         result_lines = []
    #         for i, original_line in enumerate(source_lines, start=1):
    #             if i not in lines_to_skip:
    #                 stripped_line = original_line.rstrip("\n")
    #                 annotated_line = f"{i} {stripped_line}\n"
    #                 result_lines.append(annotated_line)

    #         # print("--- REsult lines ---")
    #         # print(result_lines)
    #         # print("--- End Result lines ---")

    #         res = "".join(result_lines)
    #         res_cln = self._filter_stray_decorators(res)
    #         res_cln = re.sub(r"(^\d+ \n)(\d+ \n)+", r"\1", res_cln, flags=re.MULTILINE)
    #         return res_cln

    #     return ""

    @staticmethod
    def _build_function_class_maps(function_list: list[str]) -> list[dict[str, str]]:
        """
        Creates a list of dicts: [{"function_scope_name": scope}, ...] where `scope` is either
        the class name in which the function is defined, or "global" if
        it is defined at the top level.

        Parameters:
          function_list (list): Function names (full scope) to check

        Returns:
          list: Dictionaries with functions and their scope
        """

        results = []
        for item in function_list:
            parts = item.split(":")
            segments = [class_scope.split(".") for class_scope in parts]
            if (
                len(segments) == 1 and len(segments[0]) > 1
            ):  # If only one segment, no nested classes
                key = (
                    ".".join(segments[0][1:]) if segments[0][0] == "global" else item
                )  # Skip "global" keyword
                results.append({key: segments[0][0]})
            elif len(segments) > 1:
                results.append({item: segments[-1][0]})
        return results

    def _extract_test_fname(self, tree: Tree) -> dict[str, str]:
        """
        Builds a scope map for each call expression (test). A scope is structured using the expression descriptions.
        Each test is saved together with its scope and content.

        Parameters:
            tree (Tree): The concrete syntax tree to build a scope map from

        Returns:
            dict: A mapping of call expressions to their scopes and content
        """
        test_node = self._get_mod_test_node(tree.root_node)
        if test_node is None:
            return {}

        assert isinstance(test_node, Node)
        declaration_list = next(
            (
                child
                for child in test_node.named_children
                if child.type == "declaration_list"
            ),
            None,
        )
        assert declaration_list

        # test_fn_name: <test block>
        func_2_content = {}

        for root_child in declaration_list.named_children:
            if root_child.type != "function_item":
                continue
            f_name, f_body = self.dereference_function(root_child)
            func_2_content[f_name] = f_body

        return func_2_content

    @staticmethod
    def _find_changed_tests(
        tests_old: dict[str, str], tests_new: dict[str, str]
    ) -> list[str]:
        """
        Finds tests that have changed between two versions.

        Parameters:
            tests_old (dict): The tests in the pre-PR version of the file
            tests_new (dict): The tests in the post-PR version of the file

        Returns:
            list: All changed tests (either new of modified)
        """

        changed_tests: list[str] = []

        for func_name, body_new in tests_new.items():
            body_old = tests_old.get(func_name)
            if body_old is None:  # function is new
                changed_tests.append(func_name)
                continue

            if body_old != body_new:  # function exists but has changed
                diff = list(
                    difflib.unified_diff(body_old.splitlines(), body_new.splitlines())
                )
                if diff:
                    changed_tests.append(func_name)

        return changed_tests

    def _filter_stray_decorators(self, file_content: str) -> str:
        """
        Removes any decorators which don't belong to a function or class.

        Parameters:
            file_content (str): The content to filter

        Returns:
            str: Code without stray decorators
        """

        lines = file_content.splitlines()
        kept = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            if self._is_decorator_start(line):
                decorator_blocks = []

                while i < n and self._is_decorator_start(lines[i]):
                    block_start = i
                    block_end = self._get_decorator_end(lines, block_start)
                    block_lines = lines[block_start : block_end + 1]
                    decorator_blocks.append(block_lines)
                    i = block_end + 1

                if i < n and self._is_function_or_class_start(lines[i]):
                    for block in decorator_blocks:
                        kept.extend(block)
                else:
                    pass

            else:
                kept.append(line)
                i += 1

        return "\n".join(kept)

    @staticmethod
    def _is_decorator_start(line: str) -> bool:
        """
        Checks if a line starts with optional digits/spaces followed by '@'.
        e.g. "300 @something", "   @something", "@something"

        Parameters:
            line (str): The line to check

        Returns:
            bool: True if the line is a decorator, False otherwise
        """

        return bool(re.match(r"^\s*\d*\s*@", line))

    @staticmethod
    def _is_function_or_class_start(line: str) -> bool:
        """
        Checks if a line starts with optional digits/spaces followed by:
          - an optional 'async' then 'function' (for global function declarations),
          - 'class', or
          - an optional 'async' then an identifier followed by '(' (for class method definitions).
        e.g. "  10 function foo() {", "  async function bar() {",
             "  class Baz {", or "  async myMethod() {"

        Parameters:
            line (str): The line to check

        Returns:
            bool: True if the line is a function or class, False otherwise
        """

        return bool(
            re.match(
                r"^\s*\d*\s*(?:(?:async\s+)?function\b|class\b|(?:async\s+)?[A-Za-z_$][A-Za-z0-9:$]*\s*\()",
                line,
            )
        )

    @staticmethod
    def _get_decorator_end(lines: list, start_index: int) -> int:
        """
        Retrieves the last line index which still belongs to the decorator. Namely, if there
        are any brackets present which need to be included

        Parameters:
            lines (list): The lines to search
            start_index (int): The index of the first line to search

        Returns:
            int: The index of the last line which still belongs to the decorator
        """

        open_brackets = 0
        end_index = start_index
        i = start_index

        while i < len(lines):
            line = lines[i]
            for char in line:
                if char == "(":
                    open_brackets += 1
                elif char == ")":
                    open_brackets -= 1

            end_index = i
            i += 1

            if open_brackets == 0:
                break

        return end_index

    @staticmethod
    def _get_node_body(node: Node) -> list | None:
        """
        Return the body of a node (i.e., function / class body).

        Parameters:
            node (Node): The node to get the body of

        Returns:
            list: The body of the node
        """

        body = node.child_by_field_name("body")
        return body.named_children if body else []

    def dereference_function(self, node: Node) -> tuple[str, str]:
        """
        Return the body of a function node (i.e., function / class body) as str.

        Parameters:
            node (Node): The node to get the body of

        Returns:
            str: the function name
            str: The body of the node
        """
        assert node.type == "function_item", "Node must be a function_item"

        func_name: str = ""
        func_body: str = ""
        for child in node.named_children:
            if child.type == "identifier":
                func_name = child.text.decode("utf-8")
            else:
                func_body = child.text.decode("utf-8")
                lines = func_body.splitlines()
                func_body = "\n".join([line.strip() for line in lines if line.strip()])

        return func_name, func_body

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
