import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect


def submit_small_room_booking(
    page: Page, base_url: str, *, participants: int, end_time: str = "11:00"
) -> str:
    response = page.goto(base_url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        raise RuntimeError(f"Booking page unavailable: {response}")

    booking_date = (date.today() + timedelta(days=1)).isoformat()
    page.get_by_role("combobox", name="Переговорная").select_option("small")
    page.get_by_label("Дата").fill(booking_date)
    page.get_by_label("Начало").fill("10:00")
    page.get_by_label("Окончание").fill(end_time)
    page.get_by_label("Участники").fill(str(participants))
    page.get_by_label("Ваше имя").fill("Ирина")
    page.get_by_label("Рабочая почта").fill("qa@example.org")
    page.get_by_role("button", name="Забронировать").click()
    return booking_date


def test_small_room_accepts_four_participants(page: Page, base_url: str):
    booking_date = submit_small_room_booking(page, base_url, participants=4)

    status = page.get_by_role("status")
    expect(status).to_be_visible()
    for detail in ("Бронирование создано", "Малая", booking_date, "10:00–11:00", "Ирина"):
        expect(status).to_contain_text(detail)


def test_small_room_rejects_five_participants(page: Page, base_url: str):
    submit_small_room_booking(page, base_url, participants=5)

    expect(page.get_by_text("В комнате максимум 4 участника.", exact=True)).to_be_visible()
    expect(page.get_by_role("status")).not_to_contain_text("Бронирование создано")


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01: Roomly confirms a 29-minute booking",
    raises=AssertionError,
)
def test_booking_rejects_29_minutes(page: Page, base_url: str):
    submit_small_room_booking(page, base_url, participants=3, end_time="10:29")

    # A missing response or missing validation message must fail normally.
    status = page.get_by_role("status")
    status.wait_for(state="visible")
    message = status.inner_text()
    assert "Бронирование создано" not in message, message
    page.get_by_text(re.compile(r"30\s*мин|длительность", re.I)).wait_for(state="visible")
