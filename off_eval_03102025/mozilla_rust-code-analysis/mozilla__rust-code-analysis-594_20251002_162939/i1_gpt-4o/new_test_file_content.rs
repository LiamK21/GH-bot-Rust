#enums/src/macros.rs
#[macro_export]
macro_rules! mk_enum {
    ( $( $camel:ident ),* ) => {
        #[derive(Clone, Debug, IntoEnumIterator, PartialEq)]
        #[allow(clippy::upper_case_acronyms)]
        pub enum LANG {
            $(
                $camel,
            )*
        }
    };
}

#[macro_export]
macro_rules! mk_get_language {
    ( $( ($camel:ident, $name:ident) ),* ) => {
        pub fn get_language(lang: &LANG) -> Language {
              match lang {
                  LANG::Java => tree_sitter_java::language(),
                  LANG::Typescript => tree_sitter_typescript::language_typescript(),
                  LANG::Tsx => tree_sitter_typescript::language_tsx(),
                  LANG::Javascript => tree_sitter_javascript::language(),
                  LANG::Python => tree_sitter_python::language(),
                  LANG::Preproc => tree_sitter_preproc::language(),
                  LANG::Ccomment => tree_sitter_ccomment::language(),
                  LANG::Cpp => tree_sitter_mozcpp::language(),
                  LANG::Mozjs => tree_sitter_mozjs::language(),
                  _ => match lang {
                    $(
                        LANG::$camel => {
                            extern "C" { fn $name() -> Language; }
                            unsafe { $name() }
                        },
                    )*
                }
            }
        }
    };
}

#[macro_export]
macro_rules! mk_get_language_name {
    ( $( $camel:ident ),* ) => {
        pub fn get_language_name(lang: &LANG) -> &'static str {
            match lang {
                $(
                    LANG::$camel => stringify!($camel),
                )*
            }
        }
    };
}

#[macro_export]
macro_rules! mk_langs {
    ( $( ($camel:ident, $name:ident) ),* ) => {
        mk_enum!($( $camel ),*);
        mk_get_language!($( ($camel, $name) ),*);
        mk_get_language_name!($( $camel ),*);
    };
}

#[cfg(test)]
mod tests {
use super::get_language;
use tree_sitter::{Language, Parser};

#[test]
fn test_get_language_rust() {
    let lang = get_language(&LANG::Rust);
    let mut parser = Parser::new();
    parser.set_language(lang).expect("Error setting language");
    let code = "fn main() { println!(\"Hello, world!\"); }";
    let tree = parser.parse(code, None).unwrap();
    let root_node = tree.root_node();
    assert_eq!(root_node.kind(), "source_file");
}
}
