from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parent.parent
DOCS=[ROOT/'README.md', *sorted((ROOT/'docs').glob('*.md'))]


def anchors(text):
    result=set()
    for line in text.splitlines():
        if re.match(r'^#{1,6} ',line):
            title=re.sub(r'^#+ ', '',line).strip().lower()
            title=re.sub(r'[^\w\- ]','',title)
            result.add(title.replace(' ','-'))
    return result


class Documentation(unittest.TestCase):
    def test_local_links_and_anchors(self):
        for document in DOCS:
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',document.read_text('utf-8')):
                url=urlsplit(target)
                if url.scheme or url.netloc:
                    continue
                file=(document.parent/unquote(url.path)).resolve() if url.path else document
                with self.subTest(document=document.name,target=target):
                    self.assertTrue(file.is_file())
                    if url.fragment and file.suffix=='.md':
                        self.assertIn(unquote(url.fragment),anchors(file.read_text('utf-8')))

    def test_fenced_examples_are_closed(self):
        for document in DOCS:
            with self.subTest(document=document.name):
                self.assertEqual(sum(line.startswith('```') for line in document.read_text('utf-8').splitlines()) % 2,0)

    def test_reader_has_entry_points(self):
        text=(ROOT/'README.md').read_text('utf-8')
        for file in ['concepts.md','deployment.md','troubleshooting.md','faq.md']:
            self.assertIn(file,text)


if __name__=='__main__':unittest.main()
