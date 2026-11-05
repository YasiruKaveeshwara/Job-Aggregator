from winotify import audio

from desktop.notifications import show_windows_notification


def test_windows_notification_uses_default_sound(monkeypatch):
    calls = []

    class FakeNotification:
        def __init__(self, *, app_id, title, msg):
            calls.append(("init", app_id, title, msg))

        def set_audio(self, sound, loop):
            calls.append(("audio", str(sound), loop))

        def show(self):
            calls.append(("show",))

    monkeypatch.setattr("winotify.Notification", FakeNotification)

    show_windows_notification("Test title", "Test message")

    assert calls == [
        ("init", "Job Aggregator", "Test title", "Test message"),
        ("audio", str(audio.Default), False),
        ("show",),
    ]
