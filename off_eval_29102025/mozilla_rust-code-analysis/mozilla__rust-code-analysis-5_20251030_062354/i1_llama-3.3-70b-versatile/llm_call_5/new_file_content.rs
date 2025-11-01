#src/web/server.rs
extern crate actix_web;

use actix_web::{web, App, HttpRequest, HttpResponse, HttpServer};
use std::path::PathBuf;

use super::ast::{AstCallback, AstCfg, AstPayload};
use super::comment::{WebCommentCallback, WebCommentCfg, WebCommentPayload};
use crate::languages::action;
use crate::tools::get_language_for_file;

fn ast_parser(item: web::Json<AstPayload>, _req: HttpRequest) -> HttpResponse {
    let language = get_language_for_file(&PathBuf::from(&item.file_name));
    let payload = item.into_inner();
    let cfg = AstCfg {
        id: payload.id,
        comment: payload.comment,
        span: payload.span,
    };
    // TODO: the 4th arg should be preproc data
    HttpResponse::Ok().json(action::<AstCallback>(
        &language.unwrap(),
        payload.code.into_bytes(),
        &PathBuf::from(""),
        None,
        cfg,
    ))
}

fn comment_removal(item: web::Json<WebCommentPayload>, _req: HttpRequest) -> HttpResponse {
    let language = get_language_for_file(&PathBuf::from(&item.file_name));
    let payload = item.into_inner();
    let cfg = WebCommentCfg { id: payload.id };
    HttpResponse::Ok().json(action::<WebCommentCallback>(
        &language.unwrap(),
        payload.code.into_bytes(),
        &PathBuf::from(""),
        None,
        cfg,
    ))
}

pub fn run(host: &str, port: u32, n_threads: usize) -> std::io::Result<()> {
    println!("Run server");
    HttpServer::new(|| {
        App::new()
            .service(
                web::resource("/ast")
                    .data(web::JsonConfig::default().limit(std::u32::MAX as usize))
                    .route(web::post().to(ast_parser)),
            )
            .service(
                web::resource("/comment")
                    .data(web::JsonConfig::default().limit(std::u32::MAX as usize))
                    .route(web::post().to(comment_removal)),
            )
    })
    .workers(n_threads)
    .bind(format!("{}:{}", host, port))?
    .run()
}

// curl --header "Content-Type: application/json" --request POST --data '{"id": "1234", "file_name": "prova.cpp", "code": "int x = 1;", "comment": true, "span": true}' http://127.0.0.1:8080/ast

#[cfg(test)]
mod tests {
use actix_web::test::TestApp;
use actix_web::http::header;
use actix_web::http::StatusCode;
use serde_json::json;
use super::run;
use super::comment_removal;
use super::comment::WebCommentPayload;

#[test]
fn test_comment_removal_with_file_name() {
  let mut app = TestApp::new(super::run("127.0.0.1", 8080, 1));
  let payload = WebCommentPayload {
    id: "1234".to_string(),
    file_name: "prova.cpp".to_string(),
    code: "int x = 1;".to_string(),
  };
  let req = TestRequest::post()
    .uri("/comment")
    .header(header::CONTENT_TYPE, "application/json")
    .set_json(&payload);
  let res = app.service(req).await;
  assert_eq!(res.status(), StatusCode::OK);
}
}
