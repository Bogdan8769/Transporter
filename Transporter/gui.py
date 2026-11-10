import customtkinter as ctk
import tkintermapview
from distante import gaseste_coordonate_adresa, obtine_drum_pe_strazi
from optimizer import ruleaza_tsp_cheapest_insertion

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FereastraCurier(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Transporter AI - Optimizator Traseu Curierat")
        self.geometry("1280x760")

        self.depozit = None
        self.colete = []
        self.markere = []
        self.linie_harta = None

        # --- PANOU LATERAL STÂNGA ---
        self.meniu = ctk.CTkFrame(self, width=360, corner_radius=0)
        self.meniu.pack(side="left", fill="y")

        self.titlu = ctk.CTkLabel(self.meniu, text="🚚 Transporter AI", font=("Arial", 22, "bold"))
        self.titlu.pack(pady=(15, 5))

        self.lbl_status_ghid = ctk.CTkLabel(
            self.meniu,
            text="Pasul 1: Scrie adresa DEPOZITULUI\nsau dă click direct pe hartă",
            text_color="#3498db",
            font=("Arial", 13, "bold")
        )
        self.lbl_status_ghid.pack(pady=5, padx=15)

        # Câmp introducere adresă
        ctk.CTkLabel(self.meniu, text="📍 Adaugă oprire / adresă:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(5, 0))
        
        self.camp_adresa = ctk.CTkEntry(self.meniu, placeholder_text="Ex: Firiza 96 sau Bd. Unirii 10", height=35)
        self.camp_adresa.pack(fill="x", padx=15, pady=5)
        self.camp_adresa.bind("<Return>", lambda event: self.adauga_adresa_actiune())

        self.btn_adauga = ctk.CTkButton(
            self.meniu, text="➕ Adaugă pe Hartă", fg_color="#3498db", hover_color="#2980b9",
            height=35, font=("Arial", 12, "bold"), command=self.adauga_adresa_actiune
        )
        self.btn_adauga.pack(fill="x", padx=15, pady=5)

        # Buton Principal AI
        self.btn_calculeaza = ctk.CTkButton(
            self.meniu, text="⚡ Calculează Traseul Optim (AI)", fg_color="#2ecc71", hover_color="#27ae60",
            text_color="black", height=42, font=("Arial", 13, "bold"), command=self.calculeaza_traseu_actiune
        )
        self.btn_calculeaza.pack(fill="x", padx=15, pady=10)

        # Butoane Demo & Export
        frame_sus = ctk.CTkFrame(self.meniu, fg_color="transparent")
        frame_sus.pack(fill="x", padx=15, pady=3)

        self.btn_demo = ctk.CTkButton(frame_sus, text="🎯 Încarcă Demo", fg_color="#9b59b6", width=155, command=self.incarca_demo)
        self.btn_demo.pack(side="left", padx=(0, 5))

        self.btn_export = ctk.CTkButton(frame_sus, text="💾 Salvează TXT", fg_color="#34495e", width=155, command=self.salveaza_txt)
        self.btn_export.pack(side="right")

        # Butoane Ștergere
        frame_jos = ctk.CTkFrame(self.meniu, fg_color="transparent")
        frame_jos.pack(fill="x", padx=15, pady=5)

        self.btn_undo = ctk.CTkButton(frame_jos, text="↩ Șterge Ultimul", fg_color="#f39c12", text_color="black", width=155, command=self.sterge_ultimul)
        self.btn_undo.pack(side="left", padx=(0, 5))

        self.btn_reset = ctk.CTkButton(frame_jos, text="🗑 Resetează Tot", fg_color="#e74c3c", width=155, command=self.reseteaza_tot)
        self.btn_reset.pack(side="right")

        # Comutator Stil Hartă
        self.comutator_harta = ctk.CTkSegmentedButton(
            self.meniu, values=["Google Străzi", "Google Satelit"], command=self.schimba_harta
        )
        self.comutator_harta.set("Google Străzi")
        self.comutator_harta.pack(fill="x", padx=15, pady=10)

        # Casetă text itinerariu
        ctk.CTkLabel(self.meniu, text="📋 Foiță de Parcurs (Ordinea Livrărilor):", font=("Arial", 12, "bold")).pack(anchor="w", padx=15)
        self.text_itinerariu = ctk.CTkTextbox(self.meniu, height=140, font=("Consolas", 11))
        self.text_itinerariu.pack(fill="both", expand=True, padx=15, pady=5)
        self.text_itinerariu.insert("0.0", "Adaugă adrese sus sau dă click pe hartă.")

        # Panou Statistici Inferior
        self.lbl_statistici = ctk.CTkLabel(
            self.meniu, text="Distanță: 0.00 km | Economie AI: 0.00 km\nTimp: 0 min | Cost combustibil: 0.00 RON",
            font=("Arial", 11, "bold"), justify="left"
        )
        self.lbl_statistici.pack(side="bottom", pady=15, padx=15)

        # --- HARTA ÎN DREAPTA ---
        self.harta = tkintermapview.TkinterMapView(self, corner_radius=12)
        self.harta.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.harta.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=ro&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        self.harta.set_position(47.6567, 23.5850) # Baia Mare
        self.harta.set_zoom(14)

        # Click stânga pe hartă plasează puncte direct
        self.harta.add_left_click_map_command(self.click_harta_actiune)

    def schimba_harta(self, valoare):
        if valoare == "Google Străzi":
            self.harta.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=ro&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        else:
            self.harta.set_tile_server("https://mt0.google.com/vt/lyrs=y&hl=ro&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)

    def adauga_punct_hartas(self, lat, lon, nume):
        if self.depozit is None:
            self.depozit = [lat, lon, f"Depozit ({nume})"]
            m = self.harta.set_marker(lat, lon, text=f"🏢 DEPOZIT: {nume}", marker_color_circle="#1f538d", marker_color_outside="#2980b9")
            self.markere.append(m)
            self.lbl_status_ghid.configure(text="Pasul 2: Adaugă adresele COLETELOR", text_color="#e67e22")
        else:
            nr = len(self.colete) + 1
            eticheta = f"Colet {nr}: {nume}"
            self.colete.append([lat, lon, eticheta])
            m = self.harta.set_marker(lat, lon, text=f"📦 {eticheta}", marker_color_circle="#d35400", marker_color_outside="#e67e22")
            self.markere.append(m)
            self.lbl_status_ghid.configure(text=f"✅ {nr} colete înregistrate.", text_color="#2ecc71")
        
        self.actualizeaza_text_box()

    def adauga_adresa_actiune(self):
        text_adresa = self.camp_adresa.get().strip()
        if not text_adresa:
            return

        self.lbl_status_ghid.configure(text=f"🔍 Caut adresa: {text_adresa}...", text_color="#f1c40f")
        self.update()

        rezultat = gaseste_coordonate_adresa(text_adresa)
        if not rezultat:
            self.lbl_status_ghid.configure(text="❌ Adresa nu a fost găsită!", text_color="#e74c3c")
            return

        lat, lon, nume = rezultat[0], rezultat[1], rezultat[2]
        self.harta.set_position(lat, lon)
        self.harta.set_zoom(16)
        self.adauga_punct_hartas(lat, lon, nume)
        self.camp_adresa.delete(0, "end")

    def click_harta_actiune(self, coords):
        lat, lon = coords[0], coords[1]
        nume = "Sediu Central" if self.depozit is None else f"Locație ({lat:.4f}, {lon:.4f})"
        self.adauga_punct_hartas(lat, lon, nume)

    def actualizeaza_text_box(self):
        self.text_itinerariu.delete("0.0", "end")
        if self.depozit:
            self.text_itinerariu.insert("end", f"🏢 START: {self.depozit[2]}\n")
        for c in self.colete:
            self.text_itinerariu.insert("end", f"  • {c[2]}\n")

    def calculeaza_traseu_actiune(self):
        if not self.depozit or not self.colete:
            self.lbl_status_ghid.configure(text="⚠️ Pune depozitul și minim un colet!", text_color="#e74c3c")
            return

        self.lbl_status_ghid.configure(text="⏳ Rulam algoritmul TSP pe șosele...", text_color="#f1c40f")
        self.update()

        traseu_optim, km_optim, km_neoptimizat = ruleaza_tsp_cheapest_insertion(self.depozit, self.colete)
        puncte_sosea = obtine_drum_pe_strazi(traseu_optim)

        if self.linie_harta:
            self.linie_harta.delete()
        self.linie_harta = self.harta.set_path(puncte_sosea, color="#2ecc71", width=5)

        for m in self.markere:
            m.delete()
        self.markere.clear()

        # Replantăm markerele ordonate
        m_dep = self.harta.set_marker(self.depozit[0], self.depozit[1], text=f"🏢 START/SOSIRE", marker_color_circle="#1f538d", marker_color_outside="#2980b9")
        self.markere.append(m_dep)

        self.text_itinerariu.delete("0.0", "end")
        self.text_itinerariu.insert("end", f"0. PLECARE: {self.depozit[2]}\n")

        for pas in range(1, len(traseu_optim) - 1):
            oprire = traseu_optim[pas]
            self.text_itinerariu.insert("end", f"{pas}. LIVRARE -> {oprire[2]}\n")
            m = self.harta.set_marker(oprire[0], oprire[1], text=f"Oprirea #{pas} ({oprire[2]})", marker_color_circle="#1e8449", marker_color_outside="#2ecc71")
            self.markere.append(m)

        self.text_itinerariu.insert("end", f"{len(traseu_optim)-1}. SOSIRE: {self.depozit[2]}")

        # Statistici avansate
        economie = max(0.0, km_neoptimizat - km_optim)
        minute = int((km_optim / 35.0) * 60) + (len(self.colete) * 3)
        cost_ron = ((km_optim * 8.0) / 100.0) * 7.5

        self.lbl_statistici.configure(
            text=f"Traseu AI: {km_optim:.2f} km (Economisit: {economie:.2f} km)\n"
                 f"Timp: ~{minute} min | Cost combustibil: {cost_ron:.2f} RON"
        )
        self.lbl_status_ghid.configure(text="✅ Traseu optimizat cu succes!", text_color="#2ecc71")

    def incarca_demo(self):
        self.reseteaza_tot()
        demo = [
            (47.6533, 23.5514, "Depozit FAN Baia Mare"),
            (47.6593, 23.5818, "Str. Gheorghe Șincai 37"),
            (47.6472, 23.5691, "Vivo Mall Baia Mare"),
            (47.6661, 23.5679, "Spitalul Județean Baia Mare"),
            (47.6415, 23.5843, "Gara CFR Baia Mare")
        ]
        for lat, lon, nume in demo:
            self.adauga_punct_hartas(lat, lon, nume)
        self.harta.set_position(47.6540, 23.5700)
        self.harta.set_zoom(13)

    def salveaza_txt(self):
        continut = self.text_itinerariu.get("0.0", "end").strip()
        with open("foaie_parcurs_transporter.txt", "w", encoding="utf-8") as f:
            f.write("=== FOAIE DE PARCURS - TRANSPORTER AI ===\n\n" + continut + "\n\n" + self.lbl_statistici.cget("text"))
        self.lbl_status_ghid.configure(text="💾 Salvat în foaie_parcurs_transporter.txt", text_color="#2ecc71")

    def sterge_ultimul(self):
        if self.colete:
            self.colete.pop()
            self.markere.pop().delete()
            self.actualizeaza_text_box()
        elif self.depozit:
            self.depozit = None
            self.markere.pop().delete()
            self.actualizeaza_text_box()
            self.lbl_status_ghid.configure(text="Pasul 1: Adaugă DEPOZITUL", text_color="#3498db")

    def reseteaza_tot(self):
        if self.linie_harta:
            self.linie_harta.delete()
            self.linie_harta = None
        for m in self.markere:
            m.delete()
        self.markere.clear()
        self.depozit = None
        self.colete.clear()
        self.text_itinerariu.delete("0.0", "end")
        self.text_itinerariu.insert("0.0", "Resetat. Adaugă adrese.")
        self.lbl_statistici.configure(text="Distanță: 0.00 km | Economie AI: 0.00 km\nTimp: 0 min | Cost combustibil: 0.00 RON")
        self.lbl_status_ghid.configure(text="Pasul 1: Scrie adresa DEPOZITULUI\nsau dă click direct pe hartă", text_color="#3498db")