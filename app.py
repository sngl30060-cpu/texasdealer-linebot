import os
import random
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

app = Flask(__name__)

handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))
config = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))

players_db = {}

def create_deck():
    suits = ['♠','♥','🔷','🍀']
    ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    deck = [f"{s}{r}" for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def deal(players):
    deck = create_deck()

    hands = {}
    for p in players:
        hands[p] = [deck.pop(), deck.pop()]

    community = [deck.pop() for _ in range(5)]

    return hands, community


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle(event):

    text = event.message.text.strip()
    group_id = getattr(event.source, "group_id", None)

    if not group_id:
        return

    if group_id not in players_db:
        players_db[group_id] = []

    players = players_db[group_id]

    with ApiClient(config) as api_client:
        api = MessagingApi(api_client)

        if text == "/加入":
            name = f"玩家{len(players)+1}"
            if name not in players:
                players.append(name)

            msg = "👥 玩家名單\n\n"
            for i, p in enumerate(players):
                msg += f"{i+1}. {p}\n"

        elif text == "/發牌":

            if len(players) < 2:
                msg = "至少需要2位玩家"
            else:
                hands, community = deal(players)

                msg = "🃏 德州撲克發牌結果\n\n"

                for p in players:
                    c = hands[p]
                    msg += f"👤 {p}\n{c[0]} {c[1]}\n\n"

                msg += "━━━━━━━━━\n🌟 公共牌\n"
                msg += " ".join(community)

        elif text == "/重置":
            players_db[group_id] = []
            msg = "♻️ 已重置"

        else:
            return

        api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=msg)]
            )
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
