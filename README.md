# Live Message Room (Real-time Socket Chat - Zero Database)

Aapke requirement ke mutabik yeh simple real-time live messaging website ready hai:
- **Koi Database nahi** (Saare messages in-memory / browser me rehte hain).
- **Koi naya user aaye** toh use purane saare messages turant dikhte hain.

---

## ⚡ 2 Tarike se Use Kar Sakte Hain:

### Tarika 1: 100% Sirf Frontend (Bina kisi Server ke)
Agar aap koi server nahi chalana chahte:
1. Seedha `index.html` par double click karke browser me open karein.
2. Usi page ko 2 alag-alag tabs ya alag browser window me open karein.
3. Ek tab se message bhejein — dusre tab me turant real-time message aa jayega!
4. Jab bhi koi naya tab kholega, use purane messages pehle se load milenge (Browser LocalStorage + BroadcastChannel socket).

---

### Tarika 2: Mobile / Dusre Computer ke saath Real-time Chat
Agar aapko apne mobile phone ya kisi dusre computer ke saath live chat karni hai (jiske liye network bridge chahiye hota hai):
1. Terminal / CMD me run karein:
   ```bash
   node server.js
   ```
2. Apne browser me open karein: `http://localhost:3000`
3. Mobile se connect karne ke liye: `http://<Aapka-PC-IP>:3000`
4. Isme bhi **koi Database nahi hai** (`server.js` ke andar simple JavaScript array me messages rehte hain). Naye user ke aate hi server saare messages bhej deta hai.

