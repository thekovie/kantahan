import pytest

from kantahan_catalog.discover import (
    DiscoveredLink,
    diff_links,
    js_literal_to_json,
    load_links,
    parse_html_sections,
    parse_source_a,
    save_links,
)

SCRIPT = """const songList=[{product:"REYNA SERIES",volumes:[{volume:106,link:"https://www.mediafire.com/file/aaa/Reyna_106.pdf/file"},{volume:"104~105",link:"https://x.test/a,b:c"},]},
{product:"HDD",years:[{year:2026,months:[{month:"May",link:"https://www.mediafire.com/file/bbb/HDD_May.pdf/file"}]}]}],songListHtml=`<H2>ignored ${songList.map(x=>x)}</H2>`;
document.addEventListener("DOMContentLoaded",init)"""


def test_literal_converter_quotes_bare_keys_only_outside_strings():
    out = js_literal_to_json('{a:"x, b: c",n:1,ok:true,list:[1,2,],}')
    assert out == '{"a":"x, b: c","n":1,"ok":true,"list":[1,2]}'


def test_literal_converter_rejects_template_strings():
    with pytest.raises(ValueError):
        js_literal_to_json("{a:`x`}")


def test_source_a_volumes_and_years_are_parsed_without_executing_anything():
    links = parse_source_a(SCRIPT)
    assert [(link.section, link.label) for link in links] == [
        ("REYNA SERIES", "Volume 106"),
        ("REYNA SERIES", "Volume 104~105"),
        ("HDD", "2026 May"),
    ]
    assert links[1].url == "https://x.test/a,b:c"


def test_source_a_without_data_array_is_an_error():
    with pytest.raises(ValueError, match="songList"):
        parse_source_a("console.log(1)")


HTML = """
<button class="accordion4">REYNA SERIES</button>
<div><table><tbody>
<tr><td>VOLUME 106 SONGLIST</td><td><a href="https://www.mediafire.com/file/aaa/f.pdf/file"><img src="x"></a></td></tr>
<tr></tr>
<tr><td>VOLUME 105 SONGLIST</td><td><a href="https://www.mediafire.com/file/bbb/g.pdf/file">x</a></td></tr>
</tbody></table></div>
<button class="accordion4">T-X SERIES</button>
<table><tr><td>VOLUME 3</td><td><a href="/relative">x</a></td></tr></table>
<footer><a href="https://www.facebook.com/x">social</a></footer>
"""


def test_html_sections_give_label_and_absolute_links_per_section():
    links = parse_html_sections(HTML, "b")
    assert [(link.section, link.label) for link in links] == [
        ("REYNA SERIES", "VOLUME 106 SONGLIST"),
        ("REYNA SERIES", "VOLUME 105 SONGLIST"),
    ]
    assert all(link.source == "b" for link in links)


def test_diff_reports_added_removed_and_changed_urls():
    a = DiscoveredLink("a", "S", "Volume 1", "https://x/1")
    b = DiscoveredLink("a", "S", "Volume 2", "https://x/2")
    b2 = DiscoveredLink("a", "S", "Volume 2", "https://x/2-new")
    c = DiscoveredLink("a", "S", "Volume 3", "https://x/3")
    diff = diff_links([a, b], [b2, c])
    assert diff.added == (c,) and diff.removed == (a,) and diff.changed == ((b, b2),)


def test_links_round_trip_through_json(tmp_path):
    links = [DiscoveredLink("a", "S", "Volume 1", "https://x/1")]
    save_links(tmp_path / "d" / "links.json", links)
    assert load_links(tmp_path / "d" / "links.json") == links


def test_source_a_with_unexpected_shape_is_a_clear_error():
    with pytest.raises(ValueError, match="unexpected shape"):
        parse_source_a('const songList=[{product:"S",volumes:[{volume:1}]}];')
    with pytest.raises(ValueError, match="unexpected shape"):
        parse_source_a('const songList=[{product:"S",volumes:[{volume:1,link:{a:1}}]}];')
