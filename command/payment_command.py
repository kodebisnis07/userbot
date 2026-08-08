from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta
from pyrogram.helpers import ikb
from pyrogram.types import ReplyKeyboardRemove

from config import IS_JASA_PRIVATE, OWNER_ID
from database import dB
from helpers import ButtonUtils, Emoji, Message

transactions = {}
waktu_jkt = pytz.timezone("Asia/Jakarta")

BANK_NAME = "SeaBank"
BANK_ACCOUNT = "901291135300"
BANK_ACCOUNT_NAME = "Saiful Anwar"


async def add_transaction(user_id, month, plan):
    await dB.set_var(user_id, "plan", plan)
    expired = await dB.get_expired_date(user_id)
    if not expired:
        now = datetime.now(waktu_jkt)
        expired = now + relativedelta(months=month)
        await dB.set_expired_date(user_id, expired)


def bank_payment_buttons():
    return ikb(
        [
            [
                (
                    "✅ Kirim Bukti Transfer",
                    f"tg://openmessage?user_id={OWNER_ID}",
                    "url",
                )
            ],
            [("❌ Cancel", "batal_payment")],
        ]
    )


async def user_aggre(client, callback_query):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    del_ = await client.send_message(
        user_id, "<b>Please wait...</b>", reply_markup=ReplyKeyboardRemove()
    )
    if IS_JASA_PRIVATE:
        await del_.delete()
        await callback_query.message.delete()
        reply_markup = ikb(
            [[("OWNER", f"tg://openmessage?user_id={OWNER_ID}", "url")]]
        )
        return await client.send_message(
            user_id, "<b>Please contact OWNER below</b>", reply_markup=reply_markup
        )
    await del_.delete()
    await callback_query.message.delete()
    buttons = ButtonUtils.chose_plan()
    return await client.send_message(
        user_id,
        Message.chosePlan(),
        disable_web_page_preview=True,
        reply_markup=buttons,
    )


async def chose_plan(client, callback_query):
    await callback_query.answer()
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    plan = str(callback_query.data.split()[1])
    if plan == "lite":
        PLAN = "Lite"
    elif plan == "basic":
        PLAN = "Basic"
    elif plan == "is_pro":
        PLAN = "Pro"
    else:
        PLAN = plan.title()
    buttons = ButtonUtils.plus_minus(0, 0, plan)
    return await client.send_message(
        user_id,
        Message.TEXT_PAYMENT(0, 0, 0, PLAN, 0),
        disable_web_page_preview=True,
        reply_markup=buttons,
    )


async def kurang_tambah(client, callback_query):
    QUERY = callback_query.data.split()[0]
    BULAN = int(callback_query.data.split()[1])
    PLAN = str(callback_query.data.split()[3])
    if PLAN == "lite":
        HARGA = 10000
    elif PLAN == "basic":
        HARGA = 20000
    elif PLAN == "is_pro":
        HARGA = 30000
    else:
        return
    try:
        if QUERY == "kurang":
            if BULAN > 1:
                BULAN -= 1
        elif QUERY == "tambah":
            if BULAN < 12:
                BULAN += 1

        HARGA_DASAR = HARGA * BULAN
        if BULAN >= 12:
            DISKON = 80000
        elif BULAN >= 5:
            DISKON = 25000
        elif BULAN >= 2:
            DISKON = 10000
        else:
            DISKON = 0
        TOTAL_HARGA = HARGA_DASAR - DISKON
        buttons = ButtonUtils.plus_minus(BULAN, TOTAL_HARGA, PLAN)
        if PLAN == "lite":
            PLANNING = "Lite"
        elif PLAN == "basic":
            PLANNING = "Basic"
        else:
            PLANNING = "Pro"
        await callback_query.edit_message_text(
            Message.TEXT_PAYMENT(HARGA, TOTAL_HARGA, BULAN, PLANNING, DISKON),
            disable_web_page_preview=True,
            reply_markup=buttons,
        )
    except Exception:
        pass


async def cancel_payment(client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer()

    if user_id in transactions:
        try:
            await client.delete_messages(
                chat_id=callback_query.message.chat.id,
                message_ids=transactions[user_id]["message_id"],
            )
        except Exception:
            pass

        del transactions[user_id]

        await client.send_message(
            user_id,
            "**__📑 Transaksi Berhasil Dibatalkan.__**",
            reply_markup=ButtonUtils.start_menu(user_id),
        )
    else:
        await client.send_message(user_id, "**__❌ Tidak Ada Transaksi Yang Aktif__**")


async def confirm_pay(client, callback_query):
    await callback_query.answer()
    data = callback_query.data.split()
    month = int(data[1])
    amount = int(data[2])
    plan = str(data[3])

    if plan == "lite":
        PLAN = "Lite"
    elif plan == "basic":
        PLAN = "Basic"
    elif plan == "is_pro":
        PLAN = "Pro"
    else:
        PLAN = plan.title()

    user_id = callback_query.from_user.id
    await callback_query.message.delete()

    if amount == 0:
        return await client.send_message(user_id, "<b>The price cannot be 0.</b>")
    if month == 0:
        return await client.send_message(user_id, "<b>The month cannot be 0.</b>")

    if user_id in transactions:
        return await client.send_message(
            user_id,
            "**__📑 You still have a pending transaction.__**",
            reply_markup=ikb([[("❌ Cancel", "batal_payment")]]),
        )

    item_name = f"Sewa Userbot {PLAN} {month} Months"
    now = datetime.now(waktu_jkt)
    payment_text = f"""
<b>🏦「 BANK TRANSFER 」</b>

<blockquote expandable><b><i>📦 Item: <code>{item_name}</code>
💵 Total Payment: <code>{Message.format_rupiah(amount)}</code>
🛒 Plan: {PLAN}

🏦 Bank: <code>{BANK_NAME}</code>
💳 No. Rekening: <code>{BANK_ACCOUNT}</code>
👤 A/N: <code>{BANK_ACCOUNT_NAME}</code>

Silakan transfer sesuai nominal di atas.
Setelah transfer, klik tombol ✅ Kirim Bukti Transfer dan kirim bukti pembayaran ke ADMIN.
Aktivasi dilakukan setelah ADMIN memverifikasi pembayaran.</i></b></blockquote>

<blockquote>📅 {now.strftime('%d-%m-%Y %H:%M')}</blockquote>
"""

    sent_msg = await client.send_message(
        user_id,
        payment_text,
        reply_markup=bank_payment_buttons(),
        disable_web_page_preview=True,
    )

    transactions[user_id] = {
        "message_id": sent_msg.id,
        "done": False,
        "amount": amount,
        "month": month,
        "plan": plan,
        "item_name": item_name,
    }


async def qris_cmd(client, message):
    em = Emoji(client)
    await em.get()

    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return await message.reply(
            f"{em.gagal}**Sorry, this feature is only for the Owner.**"
        )

    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return await message.reply(
                f"{em.gagal}**Incorrect format. Use:** <code>.pay amount, description</code>"
            )
        try:
            amount_str, description = args[1].split(",", maxsplit=1)
            amount = int(amount_str.strip())
            description = description.strip()
        except ValueError:
            return await message.reply(
                f"{em.gagal}**Incorrect format. Use:** <code>.pay amount, description</code>"
            )

        if amount <= 0:
            return await message.reply(f"{em.gagal}**Amount must be greater than 0.**")

        now = datetime.now(waktu_jkt)
        payment_text = f"""
<b>🏦「 BANK TRANSFER 」</b>

<blockquote expandable><b><i>{em.profil}Item: <code>{description}</code>
{em.net}Total Payment: <code>{Message.format_rupiah(amount)}</code>

🏦 Bank: <code>{BANK_NAME}</code>
💳 No. Rekening: <code>{BANK_ACCOUNT}</code>
👤 A/N: <code>{BANK_ACCOUNT_NAME}</code>

Silakan transfer sesuai nominal di atas dan kirim bukti pembayaran ke ADMIN.</i></b></blockquote>

<blockquote>📅 {now.strftime('%d-%m-%Y %H:%M')}</blockquote>
"""
        return await message.reply(payment_text)

    except ValueError:
        return await message.reply(
            f"{em.gagal}**Invalid amount. Make sure it is a number.**"
        )


async def cancelpay_cmd(client, message):
    em = Emoji(client)
    await em.get()

    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return await message.reply(
            f"{em.gagal}**Sorry, this feature is only for the Owner.**"
        )

    if user_id in transactions:
        try:
            await client.delete_messages(
                chat_id=message.chat.id,
                message_ids=transactions[user_id]["message_id"],
            )
        except Exception:
            pass
        del transactions[user_id]

        return await message.reply(
            f"{em.sukses}**Transaction has been successfully canceled.**"
        )
    return await message.reply(
        f"{em.warn}**There is no active transaction to cancel.**"
    )
