"""GEFS fetcher placeholder; implementation requires an audited inventory record."""


def fetch_inventoried_object(source_key: str) -> None:
    raise NotImplementedError(
        f"Refusing to guess a GEFS object key ({source_key!r}); inventory the actual archive object first."
    )

