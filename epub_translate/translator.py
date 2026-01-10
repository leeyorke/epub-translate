import itertools
import queue
import threading
import time

from ebooklib import ITEM_DOCUMENT, epub
from openai import OpenAI

from .config import get_config
from .patched_ebooklib import apply_epub_patch
from .settings import (
    DEBUG_MODE,
    INPUT_MAX_TOKENS,
    MAX_LOOP_COUNT,
    MAX_NUM_THREADS,
    OUTPUT_MAX_TOKENS,
    TIMEOUT,
)
from .utils import ProgressBar, print_done, printer_thread, safe_print

apply_epub_patch()
CONFIG = get_config()


class TranslateResponse:
    def __init__(self, is_translated, status_code, data):
        self.is_translated = is_translated
        self.status_code = status_code
        self.data = data


class Storage:
    def __init__(self, extracted_content_part) -> None:
        self.extracted_content_part = extracted_content_part


def translate_epub(file_path: str, target_language: str, debug) -> None:
    global DEBUG_MODE
    DEBUG_MODE = debug

    printer = threading.Thread(target=printer_thread, daemon=True)
    printer.start()

    if not DEBUG_MODE:
        safe_print(f"[*^_^*] You are using: {CONFIG.model}")
    else:
        safe_print("[*^_^*] You are using debug mode.")

    book = epub.read_epub(file_path)
    source_language = book.get_metadata("DC", "language")[0][0]
    _translate_chapters(book, source_language, target_language)
    _set_new_language(book, target_language)
    _add_translation_chapter(book, source_language, target_language)
    new_file_path = f"{file_path.replace('.epub', '')}_{target_language}.epub"
    epub.write_epub(new_file_path, book)
    safe_print(f"[*^_^*] Translating finished! -> {new_file_path}")
    print_done.set()
    printer.join(timeout=1)


def _set_new_language(book: epub.EpubBook, target_language: str) -> None:
    for data in book.metadata.values():
        if "language" in data:
            data["language"].clear()
    book.set_language(target_language)


def _translate_chapters(
    book: epub.EpubBook, source_language: str, target_language: str
):
    translate_factory = TranslateFactory(book, source_language, target_language)
    translated_text_list = translate_factory.convert()
    chapters = translate_factory._get_all_chapter
    # 生成器有状态，转成列表取长度后，已经被遍历了，就不能迭代了，是造成epub合并失败的原因
    chapters_copy, chapters_main = itertools.tee(chapters)
    idx = 0
    progress = ProgressBar()
    with progress.bar:
        task_id = progress.bar.add_task(
            "[yellow] Merging chapter...", total=sum(1 for _ in chapters_copy)
        )

        for chapter in chapters_main:
            progress.bar.update(task_id, advance=1)
            try:
                content = translated_text_list[idx]
            except IndexError as err:
                safe_print(f"{err}")
            else:
                chapter.content = content
                idx += 1


def _is_not_chapter(chapter: epub.EpubHtml) -> bool:
    chapter_content = chapter.content.decode()
    return "<body" not in chapter_content or 'type="toc"' in chapter_content


def _size_of_string(text: str):
    return len(text.encode("utf-8"))


def _translate_chapter(
    chapter: epub.EpubHtml, source_language: str, target_language: str, *, chapter_idx
):
    chapter_content = chapter.content.decode()
    extracted_content_list = _extract_body_content(chapter_content)
    translated_contents = ""
    progress = ProgressBar()

    with progress.live_bar:
        task_id = progress.bar.add_task(
            f"[cyan] Translating chapter[{chapter_idx:02}]...",
            total=len(extracted_content_list),
        )
        for extracted_content in extracted_content_list:
            progress.bar.update(task_id, advance=1)
            time.sleep(2)
            for count in range(MAX_LOOP_COUNT):
                translated_resp = _translate_text(
                    extracted_content,
                    source_language,
                    target_language,
                )

                if translated_resp.is_translated:
                    break
                else:
                    safe_print(
                        f"[(>_<)] [{chapter_idx:02}] Maybe Timeout! tried-{count + 1}! code: {translated_resp.status_code}"
                    )
                    time.sleep(5)
            translated_contents += translated_resp.data

    return _replace_body_content(chapter_content, translated_contents).encode()


def _extract_body_content(text: str):
    start = text.find("<body")
    text = text[start:]
    start = text.find(">") + 1
    end = text.rfind("</body>")
    extracted_content = text[start:end].strip()
    extracted_content_byte_count = _size_of_string(extracted_content)
    storage = Storage(extracted_content_part="")
    split_content_list = []
    idx = 0

    if extracted_content_byte_count >= INPUT_MAX_TOKENS:
        # safe_print(
        #     f"[*^_^*] The extracted_content size more than {INPUT_MAX_TOKENS} bytes, do split!"
        # )
        extracted_content_list = extracted_content.split("\n")

        for line in extracted_content_list:
            if _size_of_string(storage.extracted_content_part) >= INPUT_MAX_TOKENS:
                split_content_list.append(storage.extracted_content_part)
                idx += 1
                # safe_print(f"[*^_^*] Part {idx} split finished！")
                storage.extracted_content_part = ""
            else:
                storage.extracted_content_part += line
                extracted_content = storage.extracted_content_part

        if len(storage.extracted_content_part) > 0:
            split_content_list.append(storage.extracted_content_part)
            storage.extracted_content_part = ""
            idx = 0
    else:
        split_content_list.append(extracted_content)

    return split_content_list


def _replace_body_content(original_text: str, new_content: str) -> str:
    start = original_text.find("<body")
    end = original_text.rfind("</body>")
    return (
        original_text[: start + original_text[start:].find(">") + 1]
        + new_content
        + original_text[end:]
    )


def _translate_text(
    text: str, source_language: str, target_language: str
) -> TranslateResponse:
    if DEBUG_MODE:
        return TranslateResponse(True, 0, f"<h1>debug mode test.</h1>{text[:100]}\n")

    prompt = (
        "You are a book translator specialized in translating "
        "HTML content while preserving the structure and tags. "
        "Translate only the inner text of the HTML, keeping all tags intact. "
        "Ensure the translation is accurate and contextually appropriate."
        f"Translate from {source_language} to {target_language}."
    )

    client = OpenAI(base_url=CONFIG.base_url, api_key=CONFIG.api_key)

    try:
        response = client.chat.completions.create(
            model=CONFIG.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"{text}"},
            ],
            stream=False,
            temperature=0.0,
            max_tokens=OUTPUT_MAX_TOKENS,
            timeout=TIMEOUT,
        )
    except Exception as err:
        return TranslateResponse(False, 1, str(err))
    else:
        if not response:
            safe_print("[(>_<)] response is null!")
            return TranslateResponse(False, 1, "(>_<): response is null!")
        elif not response.choices[0].message.content:
            safe_print("[(>_<)] response content is null!")
            return TranslateResponse(False, 1, "(>_<): response content is null!")
        else:
            return TranslateResponse(
                True, 0, _normalize_translation(response.choices[0].message.content)
            )


def _normalize_translation(text: str) -> str:
    return text[text.find("<") : text.rfind(">") + 1]


def _add_translation_chapter(
    book: epub.EpubBook, source_language: str, target_language: str
) -> None:
    content = (
        "<p style='font-style: italic; font-size: 0.9em;'>"
        "This book was translated using <strong>epub-translate</strong> — a simple CLI tool that leverages ChatGPT to translate .epub books into any language."
        "<br>"
        "You can find it on <a href='https://github.com/SpaceShaman/epub-translate' target='_blank'>GitHub</a>. If the translation meets your expectations — leave a star ⭐!</p>"
    )
    translated_resp = _translate_text(content, source_language, target_language)

    if translated_resp.is_translated:
        content = translated_resp.data

    translation_chapter = epub.EpubHtml(
        title="Translation",
        file_name="translation.xhtml",
        lang=target_language,
        uid="translation",
    )
    translation_chapter.set_content(content)
    book.add_item(translation_chapter)
    book.toc.insert(0, translation_chapter)
    book.spine.insert(0, translation_chapter)


class TranslateFactory:
    def __init__(
        self,
        book: epub.EpubBook,
        source_language,
        target_language,
        num_workers=MAX_NUM_THREADS,
    ):
        self.book = book
        self.source_language = source_language
        self.target_language = target_language
        self.task_queue = queue.Queue()
        self.result_dict = {}
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.num_workers = num_workers

    @property
    def _get_all_chapter(self):
        for chapter in self.book.get_items_of_type(ITEM_DOCUMENT):
            if _is_not_chapter(chapter):
                continue
            yield chapter

    def _worker(self):
        while True:
            index, chapter = self.task_queue.get()
            if chapter is None:
                self.task_queue.task_done()
                break
            # current_thread = threading.current_thread()
            # safe_print(f"[*^_^*] {current_thread.name} is processing chapter[{index}]")

            # 处理任务
            result = _translate_chapter(
                chapter, self.source_language, self.target_language, chapter_idx=index
            )

            # 存储结果并通知
            with self.condition:
                self.result_dict[index] = result
                self.condition.notify_all()

            self.task_queue.task_done()

    def convert(self):
        workers = []
        for _index in range(self.num_workers):
            t = threading.Thread(
                target=self._worker,
                name="Thread-" + _index.__str__(),
            )
            t.start()
            workers.append(t)

        # 把每一个章节送入队列
        for idx, chapter in enumerate(self._get_all_chapter, start=1):
            self.task_queue.put((idx, chapter))
        safe_print(f"[*^_^*] chapter total: {idx}")

        # 按顺序收集结果
        results = []
        for i, _ in enumerate(range(idx), start=1):
            with self.condition:
                # 等待当前索引的结果出现
                while i not in self.result_dict:
                    self.condition.wait()
                # 获取结果、删除结果
                results.append(self.result_dict.pop(i))

        # 结束工作线程
        for _ in range(self.num_workers):
            self.task_queue.put((-1, None))

        # 等待队列清空
        self.task_queue.join()

        # 等待工作线程结束
        for t in workers:
            t.join()

        return results
