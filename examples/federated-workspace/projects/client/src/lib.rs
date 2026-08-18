pub fn endpoint(version: u8) -> Result<&'static str, &'static str> {
    match version {
        2 => Ok("/v2/orders"),
        _ => Err("unsupported service API"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selects_v2_endpoint() {
        assert_eq!(endpoint(2), Ok("/v2/orders"));
    }
}
