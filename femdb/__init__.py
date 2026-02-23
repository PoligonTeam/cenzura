"""
Copyright 2023-2026 czubix

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import struct
import string

def intersect_sorted(lists: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    lists = sorted(lists, key=len)
    result = lists[0]
    for lst in lists[1:]:
        result = merge_intersect(result, lst)
    return result

def merge_intersect(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> list[tuple[int, int]]:
    i = j = 0
    result = []
    while i < len(a) and j < len(b):
        a_start, a_end = a[i]
        b_start, b_end = b[j]

        start = max(a_start, b_start)
        end = min(a_end, b_end)

        if start <= end:
            result.append((start, end))

        if a_end < b_end:
            i += 1
        elif a_end > b_end:
            j += 1
        else:
            i += 1
            j += 1

    return result

_struct_cache: dict[str, struct.Struct] = {}

def get_struct(fmt) -> struct.Struct:
    if fmt not in _struct_cache:
        _struct_cache[fmt] = struct.Struct(fmt)
    return _struct_cache[fmt]

def u_unpack(data: bytes, fmt: str) -> tuple[int, ...]:
    return get_struct(fmt).unpack(data)

IDXS_OFFSETS_SIZE = 12
QUESTION_SIZE = 11

ANSWERS = {
    1: True,
    0: False,
    2: "A",
    3: "B",
    4: "C"
}

class Question:
    def __init__(self, question: str, answers: list[str], answer: str | bool, media: str | None, points: int) -> None:
        self.question = question
        self.answers = answers
        self.answer = answer
        self.media = media
        self.points = points

    def __repr__(self) -> str:
        return f"<Question question={self.question!r}, answers={self.answers!r}, answer={self.answer!r}, media={self.media!r}, points={self.points!r}>"

    def __str__(self) -> str:
        return f"<Question question={self.question!r}, answers={self.answers!r}, answer={self.answer!r}, media={self.media!r}, points={self.points!r}>"

class FemDB:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.file = open(self.file_path, "rb")

        self.magic = self.file.read(4).decode()
        self.version, = u_unpack(self.file.read(4), ">I")
        self.idxs_offset, self.idxs_count, self.questions_offset = u_unpack(self.file.read(12), ">III")
        self.file.seek(self.idxs_offset)

        self.idxs_offsets = []
        
        data = self.file.read(IDXS_OFFSETS_SIZE * self.idxs_count)

        for i in range(self.idxs_count):
            i *= IDXS_OFFSETS_SIZE
            self.idxs_offsets.append(u_unpack(data[i:i+IDXS_OFFSETS_SIZE], ">III"))

    def __del__(self) -> None:
        if not self.file.closed:
            self.file.close()

    def _read_string(self, offset: int) -> str:
        self.file.seek(offset)
        a, b = u_unpack(self.file.read(8), ">II")
        self.file.seek(a)
        return self.file.read(b-a).decode()
    
    def _tokens_to_sentence(self, tokens: list[str]) -> str:
        sentence = ""
        
        for token in tokens:
            if token in string.punctuation:
                sentence += token
                continue
            sentence += " " + token

        return sentence[1:]
    
    def _get_question_content(self, offset: int) -> tuple[str, list[str]]:
        self.file.seek(offset)
        size, qsize = u_unpack(self.file.read(4), ">HH")
        data = self.file.read(size+2)
        question_offsets = [
            u_unpack(data[i:i+4], ">I")[0]
            for i in range(0, qsize, 4)
        ]
        answers_offsets = []

        if size - qsize > 2:
            ptr = qsize
            for _ in range(3):
                asize, = u_unpack(data[ptr:ptr+2], ">H")
                answers_offsets.append([
                    u_unpack(data[ptr+2+i:ptr+2+i+4], ">I")[0]
                    for i in range(0, asize, 4)
                ])
                ptr += 2 + asize

        question_tokens = [self._read_string(offset) for offset in question_offsets]
        answers_tokens = [
            [self._read_string(offset) for offset in offsets]
            for offsets in answers_offsets
        ]

        return (
            self._tokens_to_sentence(question_tokens),
            [self._tokens_to_sentence(answer_tokens) for answer_tokens in answers_tokens]
        )

    def get_question(self, qid: int) -> Question:
        self.file.seek(self.questions_offset + QUESTION_SIZE * (qid-1))

        question_offset, = u_unpack(self.file.read(4), ">I")
        question_answer = ANSWERS[ord(self.file.read(1))]
        question_has_media = ord(self.file.read(1))
        question_media_offset, = u_unpack(self.file.read(4), ">I")
        question_media = None
        question_points = ord(self.file.read(1))

        if question_has_media:
            question_media = self._read_string(question_media_offset)

        question, answers = self._get_question_content(question_offset)

        return Question(
            question,
            answers,
            question_answer,
            question_media,
            question_points
        )

    def get_ranges_for(self, *conditions: str) -> list[tuple[int, int]]:
        ranges = []
        
        for name_offset, count, idx_offset in self.idxs_offsets:
            name = self._read_string(name_offset)

            if name not in conditions:
                continue

            self.file.seek(idx_offset)
            data = self.file.read(8 * count)
            ranges.append([
                u_unpack(data[i:i+8], ">II")
                for i in range(0, len(data), 8)
            ])

        return intersect_sorted(ranges)