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
use super::LANG;
use tree_sitter_java::language;
use tree_sitter_typescript::language_typescript;
use tree_sitter_typescript::language_tsx;
use tree_sitter_javascript::language;
use tree_sitter_python::language;
use tree_sitter_preproc::language;
use tree_sitter_ccomment::language;
use tree_sitter_mozcpp::language;
use tree_sitter_mozjs::language;

#[test]
fn test_get_language() {
  let lang_java = LANG::Java;
  let lang_typescript = LANG::Typescript;
  let lang_tsx = LANG::Tsx;
  let lang_javascript = LANG::Javascript;
  let lang_python = LANG::Python;
  let lang_preproc = LANG::Preproc;
  let lang_ccomment = LANG::Ccomment;
  let lang_cpp = LANG::Cpp;
  let lang_mozjs = LANG::Mozjs;

  let expected_java = language();
  let expected_typescript = language_typescript();
  let expected_tsx = language_tsx();
  let expected_javascript = language();
  let expected_python = language();
  let expected_preproc = language();
  let expected_ccomment = language();
  let expected_cpp = language();
  let expected_mozjs = language();

  let actual_java = get_language(&lang_java);
  let actual_typescript = get_language(&lang_typescript);
  let actual_tsx = get_language(&lang_tsx);
  let actual_javascript = get_language(&lang_javascript);
  let actual_python = get_language(&lang_python);
  let actual_preproc = get_language(&lang_preproc);
  let actual_ccomment = get_language(&lang_ccomment);
  let actual_cpp = get_language(&lang_cpp);
  let actual_mozjs = get_language(&lang_mozjs);

  assert_eq!(expected_java, actual_java);
  assert_eq!(expected_typescript, actual_typescript);
  assert_eq!(expected_tsx, actual_tsx);
  assert_eq!(expected_javascript, actual_javascript);
  assert_eq!(expected_python, actual_python);
  assert_eq!(expected_preproc, actual_preproc);
  assert_eq!(expected_ccomment, actual_ccomment);
  assert_eq!(expected_cpp, actual_cpp);
  assert_eq!(expected_mozjs, actual_mozjs);
}
}
