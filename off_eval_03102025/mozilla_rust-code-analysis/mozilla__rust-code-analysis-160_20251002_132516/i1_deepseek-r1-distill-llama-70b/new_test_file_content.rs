#src/output/dump_formats.rs
#[cfg(test)]
mod tests {


#[test]
fn test_json_dump() {
    let space = FuncSpace {
        name: Some("test_function"),
        kind: SpaceKind::Function,
        start_line: 1,
        end_line: 10,
        spaces: Vec::new(),
        metrics: CodeMetrics {
            nargs: FnArgsStats::default(),
            nexits: ExitStats::default(),
            cyclomatic: CyclomaticStats::default(),
            halstead: HalsteadStats::default(),
            loc: LocStats::default(),
            nom: NomStats::default(),
            mi: MiStats::default(),
        },
    };

    let output = serde_json::to_string_pretty(&space).unwrap();
    let deserialized: FuncSpace = from_str(&output).unwrap();

    assert_eq!(deserialized.name, space.name);
    assert_eq!(deserialized.kind, space.kind);
    assert_eq!(deserialized.start_line, space.start_line);
    assert_eq!(deserialized.end_line, space.end_line);
    assert_eq!(deserialized.metrics.cyclomatic.cyclomatic(), space.metrics.cyclomatic.cyclomatic());
}
}
