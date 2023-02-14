import datetime

import asyncio
from aiogram import Bot
import requests
from bs4 import BeautifulSoup
from db.DbQuery import DbQuery
from settings import DB_NAME, TOKEN
from main import get_event_name, get_match_with_result, info_message


bot = Bot(token=TOKEN)
headers = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0"
}
queries = DbQuery(DB_NAME)
matches = queries.get_today_matches()
users = queries.get_users()
for match in matches:
    match_time_str = f"{match.get('match_day')} {match.get('start_time')}"
    match_time = datetime.datetime.strptime(
        match_time_str,
        "%d.%m.%Y %H:%M"
    )

    if match_time > datetime.datetime.today():
        continue

    req = requests.get(
        headers=headers,
        url=match.get("link")
    )
    soap = BeautifulSoup(req.text, "lxml")
    try:
        score = soap.find(id="score").text
    except Exception as e:
        continue

    match_info = {
        "match_id": match.get("match_id"),
        "result": match.get("result"),
        "is_over": match.get("is_over"),
        "winner": match.get("winner")
    }
    update_match = False
    match_name = get_event_name(
        team1_name=match.get("team1_name"),
        team1_emoji=match.get("team1_emoji"),
        team2_name=match.get("team2_name"),
        team2_emoji=match.get("team2_emoji")
    )

    match_name_params = {
        "team1_name": match.get("team1_name"),
        "team1_emoji": match.get("team1_emoji"),
        "team2_name": match.get("team2_name"),
        "team2_emoji": match.get("team2_emoji"),

    }

    match_result = ""
    if match.get("result") != score and ":" in score:
        match_info.update({
            "result": score
        })

        old_score_split = match.get("result").split(":")
        score_split = score.split(":")
        goal = 0
        if old_score_split[0] != score_split[0]:
            goal = 1
        elif old_score_split[1] != score_split[1]:
            goal = 2
        match_name_params.update({
            "winner": goal
        })

        update_match = True

    try:
        is_finished_text = soap.find(id="status").find(class_="is-finished").text
        is_finished = (is_finished_text.lower() == "конец матча")
    except Exception as e:
        is_finished = False

    if is_finished:
        score_split = score.split(":")
        winner = -1

        if int(score_split[0]) > int(score_split[1]):
            winner = 1
        elif int(score_split[0]) < int(score_split[1]):
            winner = 2
        elif int(score_split[0]) == int(score_split[1]):
            winner = 0
        match_info.update({
            "is_over": 1,
            "winner": winner,
        })
        match_name_params.update({
            "winner": winner
        })
        match_result = "Матч завершен:\n\n"
        update_match = True

    if update_match:
        queries.update_match_info(**match_info)

        match_name = get_event_name(**match_name_params)
        match_result += get_match_with_result(match_name, score)
        for user in users:
            if user.get("enable_notifications"):
                asyncio.run(info_message(user.get("tg_id"), match_result))
