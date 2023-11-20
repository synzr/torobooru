from dataclasses import dataclass


@dataclass
class URN:
    """Parsed URN data."""

    urn_provider: str
    urn_object: str
    urn_identifier: str
    urn_extra_fields: dict | None


@dataclass
class ExternalData:
    """External data."""

    urn_string: str
    urn_parsed: URN
    external_data: any
