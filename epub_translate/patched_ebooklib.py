from ebooklib import epub
from lxml import etree


def patched_get_content(self, default=None):
    """
    EbookLib Monkey Patch - 修复 EpubHtml.get_content() 丢失 head 标签内容的问题
    """
    tree = epub.parse_string(self.book.get_template(self._template_name))
    tree_root = tree.getroot()

    tree_root.set("lang", self.lang or self.book.language)
    tree_root.attrib["{%s}lang" % epub.NAMESPACES["XML"]] = (
        self.lang or self.book.language
    )

    try:
        html_tree = epub.parse_html_string(self.content)
    except Exception:
        return ""

    html_root = html_tree.getroottree()

    # create and populate head
    _head = etree.SubElement(tree_root, "head")  # type: ignore

    if self.title != "":
        _title = etree.SubElement(_head, "title")  # type: ignore
        _title.text = self.title

    for lnk in self.links:
        if lnk.get("type") == "text/javascript":
            _lnk = etree.SubElement(_head, "script", lnk)  # type: ignore
            # force <script></script>
            _lnk.text = ""
        else:
            _lnk = etree.SubElement(_head, "link", lnk)  # type: ignore

    # ====== fix ======
    head = html_root.find("head")
    if head is not None:
        # 收集已添加的 link/script 的 href/src，用于去重
        added_resources = set()
        for lnk in self.links:
            if "href" in lnk:
                added_resources.add(lnk["href"])
            if "src" in lnk:
                added_resources.add(lnk["src"])

        for i in head:
            # 跳过注释节点
            if not etree.iselement(i) or i.tag is etree.Comment:
                continue

            # 跳过 title 标签（如果已经设置了 self.title）
            if i.tag == "title" and self.title != "":
                continue

            # 避免重复添加已经在 self.links 中的 link/script
            if i.tag == "link":
                href = i.get("href")
                if href and href in added_resources:
                    continue
            elif i.tag == "script":
                src = i.get("src")
                if src and src in added_resources:
                    continue

            # 添加原始 head 中的其他元素（meta, style 等）
            _head.append(i)
    # =========================================

    # create and populate body
    _body = etree.SubElement(tree_root, "body")  # type: ignore
    if self.direction:
        _body.set("dir", self.direction)
        tree_root.set("dir", self.direction)

    body = html_tree.find("body")
    if body is not None:
        for i in body:
            _body.append(i)

    tree_str = etree.tostring(
        tree,
        pretty_print=True,  # type: ignore
        encoding="utf-8",  # type: ignore
        xml_declaration=True,  # type: ignore
    )

    return tree_str


def apply_epub_patch():
    epub.EpubHtml.get_content = patched_get_content
    print(
        "[*^_^*] EbookLib patch applied successfully - head tags will now be preserved!"
    )
