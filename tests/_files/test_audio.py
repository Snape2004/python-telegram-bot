#!/usr/bin/env python
#
# A library that provides a Python interface to the Telegram Bot API
# Copyright (C) 2015-2023
# Leandro Toledo de Souza <devs@python-telegram-bot.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].
import asyncio
import os
from pathlib import Path

import pytest

from telegram import Audio, Bot, InputFile, MessageEntity, Voice
from telegram.error import TelegramError
from telegram.helpers import escape_markdown
from telegram.request import RequestData
from tests.auxil.bot_method_checks import (
    check_defaults_handling,
    check_shortcut_call,
    check_shortcut_signature,
)
from tests.auxil.deprecations import (
    check_thumb_deprecation_warning_for_method_args,
    check_thumb_deprecation_warnings_for_args_and_attrs,
)
from tests.auxil.files import data_file
from tests.auxil.slots import mro_slots


@pytest.fixture()
def audio_file():
    with data_file("telegram.mp3").open("rb") as f:
        yield f


@pytest.fixture(scope="module")
async def audio(bot, chat_id):
    with data_file("telegram.mp3").open("rb") as f, data_file("thumb.jpg").open("rb") as thumb:
        return (await bot.send_audio(chat_id, audio=f, read_timeout=50, thumbnail=thumb)).audio


class TestAudioBase:
    caption = "Test *audio*"
    performer = "Leandro Toledo"
    title = "Teste"
    file_name = "telegram.mp3"
    duration = 3
    # audio_file_url = 'https://python-telegram-bot.org/static/testfiles/telegram.mp3'
    # Shortened link, the above one is cached with the wrong duration.
    audio_file_url = "https://goo.gl/3En24v"
    mime_type = "audio/mpeg"
    file_size = 122920
    thumb_file_size = 1427
    thumb_width = 50
    thumb_height = 50
    audio_file_id = "5a3128a4d2a04750b5b58397f3b5e812"
    audio_file_unique_id = "adc3145fd2e84d95b64d68eaa22aa33e"


class TestAudioWithoutRequest(TestAudioBase):
    def test_slot_behaviour(self, audio):
        for attr in audio.__slots__:
            assert getattr(audio, attr, "err") != "err", f"got extra slot '{attr}'"
        assert len(mro_slots(audio)) == len(set(mro_slots(audio))), "duplicate slot"

    def test_creation(self, audio):
        # Make sure file has been uploaded.
        assert isinstance(audio, Audio)
        assert isinstance(audio.file_id, str)
        assert isinstance(audio.file_unique_id, str)
        assert audio.file_id
        assert audio.file_unique_id

    def test_expected_values(self, audio):
        assert audio.duration == self.duration
        assert audio.performer is None
        assert audio.title is None
        assert audio.mime_type == self.mime_type
        assert audio.file_size == self.file_size
        assert audio.thumbnail.file_size == self.thumb_file_size
        assert audio.thumbnail.width == self.thumb_width
        assert audio.thumbnail.height == self.thumb_height

    def test_thumb_property_deprecation_warning(self, recwarn):
        audio = Audio(self.audio_file_id, self.audio_file_unique_id, self.duration, thumb=object())
        assert audio.thumb is audio.thumbnail
        check_thumb_deprecation_warnings_for_args_and_attrs(recwarn, __file__)

    def test_de_json(self, bot, audio):
        json_dict = {
            "file_id": self.audio_file_id,
            "file_unique_id": self.audio_file_unique_id,
            "duration": self.duration,
            "performer": self.performer,
            "title": self.title,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "thumbnail": audio.thumbnail.to_dict(),
        }
        json_audio = Audio.de_json(json_dict, bot)
        assert json_audio.api_kwargs == {}

        assert json_audio.file_id == self.audio_file_id
        assert json_audio.file_unique_id == self.audio_file_unique_id
        assert json_audio.duration == self.duration
        assert json_audio.performer == self.performer
        assert json_audio.title == self.title
        assert json_audio.file_name == self.file_name
        assert json_audio.mime_type == self.mime_type
        assert json_audio.file_size == self.file_size
        assert json_audio.thumbnail == audio.thumbnail

    def test_to_dict(self, audio):
        audio_dict = audio.to_dict()

        assert isinstance(audio_dict, dict)
        assert audio_dict["file_id"] == audio.file_id
        assert audio_dict["file_unique_id"] == audio.file_unique_id
        assert audio_dict["duration"] == audio.duration
        assert audio_dict["mime_type"] == audio.mime_type
        assert audio_dict["file_size"] == audio.file_size
        assert audio_dict["file_name"] == audio.file_name

    def test_equality(self, audio):
        a = Audio(audio.file_id, audio.file_unique_id, audio.duration)
        b = Audio("", audio.file_unique_id, audio.duration)
        c = Audio(audio.file_id, audio.file_unique_id, 0)
        d = Audio("", "", audio.duration)
        e = Voice(audio.file_id, audio.file_unique_id, audio.duration)

        assert a == b
        assert hash(a) == hash(b)
        assert a is not b

        assert a == c
        assert hash(a) == hash(c)

        assert a != d
        assert hash(a) != hash(d)

        assert a != e
        assert hash(a) != hash(e)

    async def test_send_with_audio(self, monkeypatch, bot, chat_id, audio):
        async def make_assertion(url, request_data: RequestData, *args, **kwargs):
            return request_data.json_parameters["audio"] == audio.file_id

        monkeypatch.setattr(bot.request, "post", make_assertion)
        assert await bot.send_audio(audio=audio, chat_id=chat_id)

    @pytest.mark.parametrize("bot_class", ["Bot", "ExtBot"])
    async def test_send_audio_thumb_deprecation_warning(
        self, recwarn, monkeypatch, bot_class, bot, raw_bot, chat_id, audio
    ):
        async def make_assertion(url, request_data: RequestData, *args, **kwargs):
            return True

        bot = raw_bot if bot_class == "Bot" else bot

        monkeypatch.setattr(bot.request, "post", make_assertion)
        await bot.send_audio(chat_id, audio, thumb="thumb")
        check_thumb_deprecation_warning_for_method_args(recwarn, __file__)

    async def test_send_audio_custom_filename(self, bot, chat_id, audio_file, monkeypatch):
        async def make_assertion(url, request_data: RequestData, *args, **kwargs):
            return list(request_data.multipart_data.values())[0][0] == "custom_filename"

        monkeypatch.setattr(bot.request, "post", make_assertion)
        assert await bot.send_audio(chat_id, audio_file, filename="custom_filename")

    @pytest.mark.parametrize("local_mode", [True, False])
    async def test_send_audio_local_files(self, monkeypatch, bot, chat_id, local_mode):
        try:
            bot._local_mode = local_mode
            # For just test that the correct paths are passed as we have no local bot API set up
            test_flag = False
            file = data_file("telegram.jpg")
            expected = file.as_uri()

            async def make_assertion(_, data, *args, **kwargs):
                nonlocal test_flag
                if local_mode:
                    test_flag = data.get("audio") == expected and data.get("thumbnail") == expected
                else:
                    test_flag = isinstance(data.get("audio"), InputFile) and isinstance(
                        data.get("thumbnail"), InputFile
                    )

            monkeypatch.setattr(bot, "_post", make_assertion)
            await bot.send_audio(chat_id, file, thumbnail=file)
            assert test_flag
        finally:
            bot._local_mode = False

    async def test_send_audio_with_local_files_throws_error_with_different_thumb_and_thumbnail(
        self, bot, chat_id
    ):
        file = data_file("telegram.jpg")
        different_file = data_file("telegram_no_standard_header.jpg")

        with pytest.raises(ValueError, match="different entities as 'thumb' and 'thumbnail'"):
            await bot.send_audio(chat_id, file, thumbnail=file, thumb=different_file)

    async def test_get_file_instance_method(self, monkeypatch, audio):
        async def make_assertion(*_, **kwargs):
            return kwargs["file_id"] == audio.file_id

        assert check_shortcut_signature(Audio.get_file, Bot.get_file, ["file_id"], [])
        assert await check_shortcut_call(audio.get_file, audio.get_bot(), "get_file")
        assert await check_defaults_handling(audio.get_file, audio.get_bot())

        monkeypatch.setattr(audio._bot, "get_file", make_assertion)
        assert await audio.get_file()


class TestAudioWithRequest(TestAudioBase):
    async def test_send_all_args(self, bot, chat_id, audio_file, thumb_file):
        message = await bot.send_audio(
            chat_id,
            audio=audio_file,
            caption=self.caption,
            duration=self.duration,
            performer=self.performer,
            title=self.title,
            disable_notification=False,
            protect_content=True,
            parse_mode="Markdown",
            thumbnail=thumb_file,
        )

        assert message.caption == self.caption.replace("*", "")

        assert isinstance(message.audio, Audio)
        assert isinstance(message.audio.file_id, str)
        assert isinstance(message.audio.file_unique_id, str)
        assert message.audio.file_unique_id is not None
        assert message.audio.file_id is not None
        assert message.audio.duration == self.duration
        assert message.audio.performer == self.performer
        assert message.audio.title == self.title
        assert message.audio.file_name == self.file_name
        assert message.audio.mime_type == self.mime_type
        assert message.audio.file_size == self.file_size
        assert message.audio.thumbnail.file_size == self.thumb_file_size
        assert message.audio.thumbnail.width == self.thumb_width
        assert message.audio.thumbnail.height == self.thumb_height
        assert message.has_protected_content

    async def test_get_and_download(self, bot, chat_id, audio):
        path = Path("telegram.mp3")
        path.unlink(missing_ok=True)

        new_file = await bot.get_file(audio.file_id)

        assert new_file.file_size == self.file_size
        assert new_file.file_unique_id == audio.file_unique_id
        assert str(new_file.file_path).startswith("https://")

        await new_file.download_to_drive("telegram.mp3")
        assert path.is_file()

    async def test_send_mp3_url_file(self, bot, chat_id, audio):
        message = await bot.send_audio(
            chat_id=chat_id, audio=self.audio_file_url, caption=self.caption
        )

        assert message.caption == self.caption

        assert isinstance(message.audio, Audio)
        assert isinstance(message.audio.file_id, str)
        assert isinstance(message.audio.file_unique_id, str)
        assert message.audio.file_unique_id is not None
        assert message.audio.file_id is not None
        assert message.audio.duration == audio.duration
        assert message.audio.mime_type == audio.mime_type
        assert message.audio.file_size == audio.file_size

    async def test_send_audio_caption_entities(self, bot, chat_id, audio):
        test_string = "Italic Bold Code"
        entities = [
            MessageEntity(MessageEntity.ITALIC, 0, 6),
            MessageEntity(MessageEntity.ITALIC, 7, 4),
            MessageEntity(MessageEntity.ITALIC, 12, 4),
        ]
        message = await bot.send_audio(
            chat_id, audio, caption=test_string, caption_entities=entities
        )

        assert message.caption == test_string
        assert message.caption_entities == tuple(entities)

    @pytest.mark.parametrize("default_bot", [{"parse_mode": "Markdown"}], indirect=True)
    async def test_send_audio_default_parse_mode_1(self, default_bot, chat_id, audio_file):
        test_string = "Italic Bold Code"
        test_markdown_string = "_Italic_ *Bold* `Code`"

        message = await default_bot.send_audio(chat_id, audio_file, caption=test_markdown_string)
        assert message.caption_markdown == test_markdown_string
        assert message.caption == test_string

    @pytest.mark.parametrize("default_bot", [{"parse_mode": "Markdown"}], indirect=True)
    async def test_send_audio_default_parse_mode_2(self, default_bot, chat_id, audio_file):
        test_markdown_string = "_Italic_ *Bold* `Code`"

        message = await default_bot.send_audio(
            chat_id, audio_file, caption=test_markdown_string, parse_mode=None
        )
        assert message.caption == test_markdown_string
        assert message.caption_markdown == escape_markdown(test_markdown_string)

    @pytest.mark.parametrize("default_bot", [{"parse_mode": "Markdown"}], indirect=True)
    async def test_send_audio_default_parse_mode_3(self, default_bot, chat_id, audio_file):
        test_markdown_string = "_Italic_ *Bold* `Code`"

        message = await default_bot.send_audio(
            chat_id, audio_file, caption=test_markdown_string, parse_mode="HTML"
        )
        assert message.caption == test_markdown_string
        assert message.caption_markdown == escape_markdown(test_markdown_string)

    @pytest.mark.parametrize("default_bot", [{"protect_content": True}], indirect=True)
    async def test_send_audio_default_protect_content(self, default_bot, chat_id, audio):
        tasks = asyncio.gather(
            default_bot.send_audio(chat_id, audio),
            default_bot.send_audio(chat_id, audio, protect_content=False),
        )
        protected, unprotected = await tasks
        assert protected.has_protected_content
        assert not unprotected.has_protected_content

    async def test_resend(self, bot, chat_id, audio):
        message = await bot.send_audio(chat_id=chat_id, audio=audio.file_id)
        assert message.audio == audio

    async def test_error_send_empty_file(self, bot, chat_id):
        with Path(os.devnull).open("rb") as audio_file, pytest.raises(TelegramError):
            await bot.send_audio(chat_id=chat_id, audio=audio_file)

    async def test_error_send_empty_file_id(self, bot, chat_id):
        with pytest.raises(TelegramError):
            await bot.send_audio(chat_id=chat_id, audio="")

    async def test_error_send_without_required_args(self, bot, chat_id):
        with pytest.raises(TypeError):
            await bot.send_audio(chat_id=chat_id)
