# SuperAgentBot — kuchaytirilgan versiya

## O'rnatish
1. Ushbu fayllarni `C:\SuperAgentBot` papkasiga ko'chiring (eski `main.py`, `ai_handler.py`,
   `keep_alive.py`, `requirements.txt` fayllarini almashtiring — eskisidan nusxa saqlab qo'ying).
2. `.env` faylingizni saqlang, lekin `.env.example` dagi yangi qatorlarni qo'shing.
3. Kutubxonalarni yangilang:
   ```
   pip install -r requirements.txt
   ```
4. Ishga tushiring:
   ```
   python main.py
   ```

## Muhim: zaxira API kalitlari
Bot endi bir nechta provayder bilan ishlaydi. Gemini limitga tushsa yoki yiqilsa —
avtomatik boshqasiga o'tadi. `.env` ga quyidagilardan kamida bittasini qo'shing (bepul):

- `GROQ_API_KEY` — console.groq.com (juda tez, kunlik bepul limit katta)
- `OPENROUTER_API_KEY` — openrouter.ai (bepul modellar bor)
- `CEREBRAS_API_KEY` — cloud.cerebras.ai
- `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` — boshqa Google akkauntlardan olingan kalitlar

Nechta kalit ko'p bo'lsa, bot shuncha uzilmay ishlaydi.

## Yangi buyruq
`/holat` — bot ish vaqti, joylangan postlar soni, qaysi AI modellari tirik,
antidoping mavzularidan nechtasi ishlatilgani.

Brauzerda: `http://localhost:8080/health` — to'liq texnik holat (JSON).

## Xavfsizlik
- Eski `ai_handler.py` ichida GitHub PAT ochiq yozilgan edi. Uni GitHub'da
  **darhol bekor qiling** (Settings → Developer settings → Tokens → Revoke).
- Bot tokeningizni ham BotFather orqali yangilashni tavsiya qilaman.
