import os

import pytest

from originsort.metadata import read_zone_identifier


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-specific")
def test_reads_zone_identifier_stream(tmp_path) -> None:
    downloaded_file = tmp_path / "lecture.pdf"
    downloaded_file.write_bytes(b"pdf")
    stream = f"{downloaded_file}:Zone.Identifier"
    with open(stream, "w", encoding="utf-8") as zone_identifier:
        zone_identifier.write(
            "[ZoneTransfer]\n"
            "ZoneId=3\n"
            "ReferrerUrl=https://eclass.dongguk.edu/mod/ubboard/article.php?"
            "id=150765&bwid=188410\n"
            "HostUrl=https://eclass.dongguk.edu/pluginfile.php/922589/file.pdf\n"
        )

    metadata = read_zone_identifier(downloaded_file)

    assert metadata is not None
    assert metadata.referrer_url is not None
    assert "id=150765" in metadata.referrer_url
    assert metadata.host_url is not None
    assert "pluginfile.php" in metadata.host_url
