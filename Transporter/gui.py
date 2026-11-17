"""Fereastra principală Transporter AI.

Fișiere folosite:
  stil.py  - culori, adrese de hărți, texte
  pini.py  - desenarea pin-urilor și a logo-ului
  colete.py / distante.py / optimizer.py - logica (neschimbate)

Ordinea din această clasă:
  1. Pornire și utilitare
  2. Panoul din stânga (construire)
  3. Harta
  4. Pin-urile
  5. Lista de opriri
  6. Statistici și pași
  7. Calcul în fundal
  8. Acțiunile butoanelor
"""
import threading
import time
import tkinter.font as tkfont
from tkinter import filedialog, messagebox

import customtkinter as ctk
import tkintermapview
from PIL import ImageTk

from colete import date_colet, citeste_csv, ora_in_minute, format_ora
from distante import gaseste_coordonate_adresa, obtine_drum_pe_strazi
from optimizer import ruleaza_tsp_cheapest_insertion
from pini import construieste_pin, construieste_logo, nume_scurt, fmt_timp
from stil import (BG, PANEL, CAMP, CARD, CARD2, LINE, TEXT, MUTED, FAINT, INK,
                  CIAN, CIAN_H, INDIGO, INDIGO_H, AMBRA, OPRIRE, VERDE, ROSU,
                  TILE_NOAPTE, TILE_STRAZI, TILE_SATELIT, TXT_CALC, TXT_RECALC)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class FereastraCurier(ctk.CTk):

    # ════════════════════ 1. PORNIRE ȘI UTILITARE ════════════════════
    def __init__(self):
        super().__init__()
        self.title("Transporter AI · Optimizator traseu curierat")
        self.geometry("1440x860")
        self.minsize(1180, 720)
        self.configure(fg_color=BG)
        self._alege_fonturi()

        # --- datele aplicației ---
        self.depozit = None        # [lat, lon, nume]
        self.colete = []           # fiecare: [lat, lon, nume, kg, m3, de_la, pana_la]  (fără limită)
        self.rezultat = None       # traseul optimizat (dict) sau None

        # --- ce e desenat pe ecran ---
        self.markere = []          # pin-urile de pe hartă
        self.linii = []            # liniile traseului
        self.carduri = {}          # cardurile din listă, după cheie
        self._poze = {}            # imaginile pin-urilor (trebuie păstrate în memorie)
        self._selectat = None

        # --- stare internă ---
        self._ocupat = False       # True cât timp rulează o operație în fundal
        self._t_marker = 0.0       # momentul ultimului click pe un pin

        self._construieste_sidebar()
        self._construieste_harta()

        self.actualizeaza_pasi()
        self.reseteaza_kpi()
        self.randeaza_opriri()
        self.seteaza_status("Setează depozitul: scrie o adresă sau dă click pe hartă.", "info")

    def _alege_fonturi(self):
        disponibile = set(tkfont.families(self))
        self.familie = next((f for f in ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text",
                                         "Helvetica Neue", "Ubuntu", "Arial") if f in disponibile), "Helvetica")

    def f(self, size, bold=False):
        """Font cu mărimea dorită."""
        return ctk.CTkFont(family=self.familie, size=size, weight="bold" if bold else "normal")

    def _stil_camp(self):
        """Aspectul comun al tuturor câmpurilor de text."""
        return dict(height=40, corner_radius=10, fg_color=CAMP, border_color=LINE, border_width=1,
                    text_color=TEXT, placeholder_text_color=FAINT, font=self.f(13))

    def _card(self, parent, titlu, subtitlu=None):
        """Un card cu titlu (și subtitlu opțional); returnează cardul ca să pui conținut în el."""
        c = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14, border_width=1, border_color=LINE)
        c.pack(fill="x", padx=(0, 6), pady=(0, 12))
        ctk.CTkLabel(c, text=titlu, font=self.f(14, True), text_color=TEXT, anchor="w").pack(
            anchor="w", padx=16, pady=(14, 2 if subtitlu else 10))
        if subtitlu:
            ctk.CTkLabel(c, text=subtitlu, font=self.f(11), text_color=MUTED, anchor="w", justify="left",
                         wraplength=330).pack(anchor="w", padx=16, pady=(0, 10))
        return c

    def seteaza_status(self, text, tip="info"):
        """Mesajul din căsuța de status. tip: info / ok / warn / work / err."""
        culori = {"info": CIAN, "ok": VERDE, "warn": AMBRA, "work": AMBRA, "err": ROSU}
        self.punct_status.configure(text_color=culori.get(tip, CIAN))
        self.lbl_status.configure(text=text)

    # ════════════════════ 2. PANOUL DIN STÂNGA ════════════════════
    def _construieste_sidebar(self):
        sb = ctk.CTkFrame(self, width=440, corner_radius=0, fg_color=PANEL)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        ctk.CTkFrame(self, width=1, corner_radius=0, fg_color=LINE).pack(side="left", fill="y")
        self.sidebar = sb

        self._construieste_antet(sb)
        self._construieste_pasi(sb)
        self._construieste_status(sb)
        self._construieste_selector_tab(sb)
        self._construieste_subsol(sb)          # înainte de conținut, ca să rămână mereu vizibil
        self._construieste_tab_planificare(sb)
        self._construieste_tab_traseu(sb)
        self.tab_plan.pack(fill="both", expand=True, padx=(16, 8), pady=(14, 0))

    def _construieste_antet(self, sb):
        antet = ctk.CTkFrame(sb, fg_color="transparent")
        antet.pack(fill="x", padx=22, pady=(22, 0))
        logo = construieste_logo()
        self._logo = ctk.CTkImage(light_image=logo, dark_image=logo, size=(46, 46))
        ctk.CTkLabel(antet, image=self._logo, text="").pack(side="left")
        bloc = ctk.CTkFrame(antet, fg_color="transparent")
        bloc.pack(side="left", padx=14)
        ctk.CTkLabel(bloc, text="Transporter AI", font=self.f(22, True), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(bloc, text="Traseu optim pentru curieri", font=self.f(12), text_color=MUTED).pack(anchor="w")

    def _construieste_pasi(self, sb):
        """Cele 3 căsuțe: Depozit · Colete · Traseu."""
        pasi = ctk.CTkFrame(sb, fg_color="transparent")
        pasi.pack(fill="x", padx=22, pady=(20, 0))
        self.chip_pasi = []
        for i, nume in enumerate(("Depozit", "Colete", "Traseu")):
            pasi.grid_columnconfigure(i, weight=1, uniform="p")
            ch = ctk.CTkFrame(pasi, corner_radius=10, fg_color=CARD, border_width=1, border_color=LINE)
            ch.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            badge = ctk.CTkLabel(ch, text=str(i + 1), width=22, height=22, corner_radius=11,
                                 fg_color=CARD2, text_color=MUTED, font=self.f(11, True))
            badge.pack(side="left", padx=(10, 6), pady=8)
            txt = ctk.CTkLabel(ch, text=nume, font=self.f(12, True), text_color=MUTED)
            txt.pack(side="left", padx=(0, 10))
            self.chip_pasi.append((ch, badge, txt))

    def _construieste_status(self, sb):
        st = ctk.CTkFrame(sb, corner_radius=10, fg_color=CARD, border_width=1, border_color=LINE)
        st.pack(fill="x", padx=22, pady=(12, 0))
        self.punct_status = ctk.CTkLabel(st, text="●", font=self.f(12), text_color=CIAN, width=14)
        self.punct_status.pack(side="left", padx=(12, 6), pady=10)
        self.lbl_status = ctk.CTkLabel(st, text="", font=self.f(12), text_color=TEXT, anchor="w",
                                       justify="left", wraplength=340)
        self.lbl_status.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)

    def _construieste_selector_tab(self, sb):
        self.tab_sel = ctk.CTkSegmentedButton(
            sb, values=["Planificare", "Traseu"], command=self.schimba_tab, height=38, corner_radius=10,
            fg_color="#0A0F19", selected_color=CARD2, selected_hover_color=CARD2,
            unselected_color="#0A0F19", unselected_hover_color=CARD, text_color=TEXT, font=self.f(13, True))
        self.tab_sel.pack(fill="x", padx=22, pady=(16, 0))
        self.tab_sel.set("Planificare")

    def _construieste_subsol(self, sb):
        """Butonul mare de calcul și bara de progres."""
        subsol = ctk.CTkFrame(sb, fg_color="transparent")
        subsol.pack(side="bottom", fill="x", padx=22, pady=(8, 22))
        self.bara = ctk.CTkProgressBar(subsol, height=4, mode="indeterminate", progress_color=CIAN, fg_color=LINE)
        self.btn_calculeaza = ctk.CTkButton(
            subsol, text=TXT_CALC, height=50, corner_radius=12, fg_color=CIAN, hover_color=CIAN_H,
            text_color=INK, text_color_disabled="#3B6F78", font=self.f(15, True),
            command=self.calculeaza_traseu_actiune)
        self.btn_calculeaza.pack(fill="x")

    # ---- Tab „Planificare" ----
    def _construieste_tab_planificare(self, sb):
        self.tab_plan = ctk.CTkScrollableFrame(sb, fg_color="transparent", scrollbar_button_color=LINE,
                                               scrollbar_button_hover_color=FAINT)
        self._card_adresa(self.tab_plan)
        self._card_detalii_colet(self.tab_plan)
        self._card_plecare_import(self.tab_plan)
        self._butoane_rapide(self.tab_plan)

    def _card_adresa(self, parinte):
        c = self._card(parinte, "Adaugă o oprire", "Scrie o adresă sau dă click pe hartă. Prima oprire devine depozit.")
        self.camp_adresa = ctk.CTkEntry(c, placeholder_text="Ex: Firiza 96 sau Bd. Unirii 10", **self._stil_camp())
        self.camp_adresa.pack(fill="x", padx=16)
        self.camp_adresa.bind("<Return>", lambda e: self.adauga_adresa_actiune())
        self.btn_adauga = ctk.CTkButton(c, text="Adaugă pe hartă", height=40, corner_radius=10, fg_color=INDIGO,
                                        hover_color=INDIGO_H, font=self.f(13, True),
                                        command=self.adauga_adresa_actiune)
        self.btn_adauga.pack(fill="x", padx=16, pady=(10, 16))

    def _card_detalii_colet(self, parinte):
        """Câmpurile kg, m³, de la, până la (în această ordine, cum așteaptă date_colet)."""
        c = self._card(parinte, "Detalii colet", "Se aplică următoarelor colete adăugate.")
        grila = ctk.CTkFrame(c, fg_color="transparent")
        grila.pack(fill="x", padx=16, pady=(0, 16))
        grila.grid_columnconfigure((0, 1), weight=1, uniform="c")
        self.campuri_colet = []
        specs = [("Greutate (kg)", "1"), ("Volum (m³)", "0.01"),
                 ("Livrare de la (HH:MM)", "08:00"), ("Livrare până la (HH:MM)", "18:00")]
        for i, (eticheta, valoare) in enumerate(specs):
            rand, col = divmod(i, 2)
            cel = ctk.CTkFrame(grila, fg_color="transparent")
            cel.grid(row=rand, column=col, sticky="ew", padx=(0, 6) if col == 0 else (6, 0),
                     pady=(0, 10) if rand == 0 else 0)
            ctk.CTkLabel(cel, text=eticheta, font=self.f(11), text_color=MUTED).pack(anchor="w", pady=(0, 4))
            camp = ctk.CTkEntry(cel, **self._stil_camp())
            camp.insert(0, valoare)
            camp.pack(fill="x")
            self.campuri_colet.append(camp)

    def _card_plecare_import(self, parinte):
        c = self._card(parinte, "Plecare și import")
        rand = ctk.CTkFrame(c, fg_color="transparent")
        rand.pack(fill="x", padx=16)
        ctk.CTkLabel(rand, text="Plecare din depozit (HH:MM)", font=self.f(12), text_color=MUTED).pack(side="left")
        self.camp_plecare = ctk.CTkEntry(rand, width=96, justify="center", **self._stil_camp())
        self.camp_plecare.insert(0, "08:00")
        self.camp_plecare.pack(side="right")
        ctk.CTkButton(c, text="Importă colete din CSV", height=40, corner_radius=10, fg_color=CARD2,
                      hover_color=LINE, border_width=1, border_color=LINE, text_color=TEXT, font=self.f(13, True),
                      command=self.importa_csv).pack(fill="x", padx=16, pady=(12, 16))

    def _butoane_rapide(self, parinte):
        """Demo · Anulează · Resetează."""
        rand = ctk.CTkFrame(parinte, fg_color="transparent")
        rand.pack(fill="x", padx=(0, 6), pady=(0, 12))
        rand.grid_columnconfigure((0, 1, 2), weight=1, uniform="a")
        butoane = [("Demo", INDIGO, INDIGO_H, "#FFFFFF", self.incarca_demo),
                   ("↩  Anulează", CARD2, LINE, TEXT, self.sterge_ultimul),
                   ("Resetează", "#3A1A24", "#4D202D", ROSU, self.reseteaza_tot)]
        creati = []
        for i, (text, fg, hover, culoare_text, comanda) in enumerate(butoane):
            b = ctk.CTkButton(rand, text=text, height=38, corner_radius=10, fg_color=fg, hover_color=hover,
                              text_color=culoare_text, font=self.f(12, True), command=comanda)
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0))
            creati.append(b)
        self.btn_demo, self.btn_undo, self.btn_reset = creati

    # ---- Tab „Traseu" ----
    def _construieste_tab_traseu(self, sb):
        """Tot tab-ul se derulează împreună (indicatori + listă), deci lista nu mai e îngustată
        și poate avea oricâte opriri."""
        self.tab_traseu = ctk.CTkScrollableFrame(sb, fg_color="transparent", scrollbar_button_color=LINE,
                                                 scrollbar_button_hover_color=FAINT)
        t = self.tab_traseu

        # cei 4 indicatori
        grila = ctk.CTkFrame(t, fg_color="transparent")
        grila.pack(fill="x", padx=(6, 6))
        grila.grid_columnconfigure((0, 1), weight=1, uniform="k")
        self.kpi = {}
        indicatori = [("dist", "Distanță"), ("eco", "Economisit de AI"),
                      ("timp", "Timp estimat"), ("cost", "Combustibil")]
        for i, (cheie, eticheta) in enumerate(indicatori):
            tile = ctk.CTkFrame(grila, corner_radius=12, fg_color=CARD, border_width=1, border_color=LINE)
            tile.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 5) if i % 2 == 0 else (5, 0), pady=(0, 10))
            ctk.CTkLabel(tile, text=eticheta, font=self.f(11), text_color=MUTED).pack(anchor="w", padx=14, pady=(12, 0))
            valoare = ctk.CTkLabel(tile, text="—", font=self.f(22, True), text_color=TEXT)
            valoare.pack(anchor="w", padx=14, pady=(0, 12))
            self.kpi[cheie] = valoare

        self.lbl_incarcatura = ctk.CTkLabel(t, text="", font=self.f(12), text_color=MUTED, anchor="w")
        self.lbl_incarcatura.pack(fill="x", padx=(8, 6), pady=(0, 8))

        # titlul listei + butonul de export
        cap = ctk.CTkFrame(t, fg_color="transparent")
        cap.pack(fill="x", padx=(6, 6), pady=(4, 8))
        ctk.CTkLabel(cap, text="Foaie de parcurs", font=self.f(14, True), text_color=TEXT).pack(side="left")
        self.lbl_nr_opriri = ctk.CTkLabel(cap, text="0 opriri", font=self.f(11, True), text_color=MUTED,
                                          fg_color=CARD2, corner_radius=8, width=64, height=22)
        self.lbl_nr_opriri.pack(side="left", padx=10)
        self.btn_export = ctk.CTkButton(cap, text="Salvează TXT", width=104, height=30, corner_radius=8,
                                        fg_color=CARD2, hover_color=LINE, text_color=TEXT, font=self.f(12, True),
                                        command=self.salveaza_txt)
        self.btn_export.pack(side="right")

        # aici se pun cardurile opririlor
        self.lista = ctk.CTkFrame(t, fg_color="transparent")
        self.lista.pack(fill="x", padx=(4, 2))

    def schimba_tab(self, valoare):
        self.tab_sel.set(valoare)
        if valoare == "Traseu":
            self.tab_plan.pack_forget()
            self.tab_traseu.pack(fill="both", expand=True, padx=(16, 8), pady=(14, 0))
        else:
            self.tab_traseu.pack_forget()
            self.tab_plan.pack(fill="both", expand=True, padx=(16, 8), pady=(14, 0))

    # ════════════════════ 3. HARTA ════════════════════
    def _construieste_harta(self):
        dr = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        dr.pack(side="right", fill="both", expand=True)

        # bara de sus: legendă (stânga) + comenzi (dreapta)
        bara = ctk.CTkFrame(dr, fg_color="transparent")
        bara.pack(fill="x", padx=18, pady=(16, 12))
        for text, culoare in (("Depozit", INDIGO), ("Colet", AMBRA), ("Oprire în traseu", OPRIRE)):
            ctk.CTkLabel(bara, text="●", text_color=culoare, font=self.f(14)).pack(side="left")
            ctk.CTkLabel(bara, text=text, font=self.f(12), text_color=MUTED).pack(side="left", padx=(4, 18))

        self.comutator_harta = ctk.CTkSegmentedButton(
            bara, values=["Noapte", "Străzi", "Satelit"], command=self.schimba_harta, height=34, corner_radius=10,
            fg_color=CARD, selected_color=CARD2, selected_hover_color=CARD2, unselected_color=CARD,
            unselected_hover_color=CARD2, text_color=TEXT, font=self.f(12, True))
        self.comutator_harta.pack(side="right")
        self.comutator_harta.set("Noapte")
        self.sw_etichete = ctk.CTkSwitch(bara, text="Etichete pe hartă", command=self.redesenare_markere,
                                         progress_color=CIAN, fg_color=LINE, button_color=TEXT,
                                         button_hover_color="#FFFFFF", text_color=MUTED, font=self.f(12))
        self.sw_etichete.select()
        self.sw_etichete.pack(side="right", padx=(0, 20))

        # harta propriu-zisă
        try:
            self.harta = tkintermapview.TkinterMapView(dr, corner_radius=14, bg_color=BG)
        except TypeError:  # versiune mai veche de tkintermapview
            self.harta = tkintermapview.TkinterMapView(dr, corner_radius=14)
        self.harta.pack(fill="both", expand=True, padx=(0, 18), pady=(0, 18))
        try:
            self.harta.canvas.configure(bg="#0B101B")
        except Exception:
            pass
        self.harta.set_tile_server(TILE_NOAPTE, max_zoom=19)
        self.harta.set_position(47.6567, 23.5850)  # Baia Mare
        self.harta.set_zoom(14)
        self.harta.add_left_click_map_command(self.click_harta_actiune)

    def schimba_harta(self, valoare):
        if valoare == "Noapte":
            self.harta.set_tile_server(TILE_NOAPTE, max_zoom=19)
        elif valoare == "Străzi":
            self.harta.set_tile_server(TILE_STRAZI, max_zoom=22)
        else:
            self.harta.set_tile_server(TILE_SATELIT, max_zoom=22)

    def click_harta_actiune(self, coords):
        if time.time() - self._t_marker < 0.5 or self._ocupat:
            return  # click-ul a nimerit un pin existent
        lat, lon = coords[0], coords[1]
        nume = "Sediu Central" if self.depozit is None else f"Locație ({lat:.4f}, {lon:.4f})"
        self.adauga_punct_hartas(lat, lon, nume)

    def deseneaza_ruta(self, puncte):
        """Conturul închis dedesubt + linia cian deasupra, ca să se vadă pe orice hartă."""
        self.sterge_ruta()
        self.linii.append(self.harta.set_path(puncte, color="#050A12", width=9))
        self.linii.append(self.harta.set_path(puncte, color=CIAN, width=5))

    def sterge_ruta(self):
        for linie in self.linii:
            try:
                linie.delete()
            except Exception:
                pass
        self.linii.clear()

    def incadreaza_puncte(self, puncte):
        """Mută și mărește harta ca să se vadă toate punctele."""
        if not puncte:
            return
        lats = [p[0] for p in puncte]
        lons = [p[1] for p in puncte]
        if len(puncte) == 1 or (max(lats) - min(lats) < 1e-5 and max(lons) - min(lons) < 1e-5):
            self.harta.set_position(lats[0], lons[0])
            self.harta.set_zoom(16)
            return
        ml = (max(lats) - min(lats)) * 0.15 + 0.0008
        mo = (max(lons) - min(lons)) * 0.15 + 0.0008
        try:
            self.harta.fit_bounding_box((max(lats) + ml, min(lons) - mo), (min(lats) - ml, max(lons) + mo))
        except Exception:
            self.harta.set_position(sum(lats) / len(lats), sum(lons) / len(lons))
            self.harta.set_zoom(13)

    # ════════════════════ 4. PIN-URILE ════════════════════
    def _poza_pin(self, culoare, simbol, eticheta, culoare_text):
        cheie = (culoare, simbol, eticheta, culoare_text)
        if cheie not in self._poze:
            self._poze[cheie] = ImageTk.PhotoImage(construieste_pin(*cheie))
        return self._poze[cheie]

    def _pune_pin(self, punct, simbol, culoare, culoare_text, eticheta, cheie):
        """Pune un pin pe hartă. `cheie` leagă pinul de cardul lui din listă."""
        icon = self._poza_pin(culoare, simbol, eticheta if self.sw_etichete.get() else None, culoare_text)
        comanda = lambda _m, k=cheie: self.la_click_pin(k)
        try:
            m = self.harta.set_marker(punct[0], punct[1], icon=icon, icon_anchor="s", command=comanda)
        except TypeError:  # versiune mai veche de tkintermapview
            m = self.harta.set_marker(punct[0], punct[1], icon=icon, command=comanda)
        self.markere.append(m)

    def _pin_colet(self, i, colet):
        self._pune_pin(colet, str(i), AMBRA, "#1B1200", nume_scurt(colet[2], 26), i)

    def redesenare_markere(self):
        """Șterge toate pin-urile și le pune din nou, după starea curentă."""
        for m in self.markere:
            m.delete()
        self.markere.clear()
        if not self.depozit:
            return
        if self.rezultat:
            traseu = self.rezultat["traseu"]
            self._pune_pin(self.depozit, "home", INDIGO, "#FFFFFF", "Start / sosire", "dep")
            for pas in range(1, len(traseu) - 1):
                oprire = traseu[pas]
                self._pune_pin(oprire, str(pas), OPRIRE, "#FFFFFF", nume_scurt(oprire[2], 26), pas)
        else:
            self._pune_pin(self.depozit, "home", INDIGO, "#FFFFFF", nume_scurt(self.depozit[2], 26), "dep")
            for i, colet in enumerate(self.colete, start=1):
                self._pin_colet(i, colet)

    def la_click_pin(self, cheie):
        self._t_marker = time.time()
        self.schimba_tab("Traseu")
        self.selecteaza_oprire(cheie, scroll=True)

    def la_click_card(self, cheie):
        self.selecteaza_oprire(cheie, scroll=False)
        punct = self._punct_pentru(cheie)
        if punct:
            self.harta.set_position(punct[0], punct[1])
            self.harta.set_zoom(max(self.harta.zoom, 16))

    def _punct_pentru(self, cheie):
        if cheie in ("dep", "sosire"):
            return self.depozit
        if self.rezultat:
            return self.rezultat["traseu"][cheie]
        return self.colete[cheie - 1] if 1 <= cheie <= len(self.colete) else None

    # ════════════════════ 5. LISTA DE OPRIRI ════════════════════
    def _leaga(self, widget, comanda):
        """Face tot cardul (și ce e în el) clickabil."""
        try:
            widget.bind("<Button-1>", comanda)
        except Exception:
            pass
        for copil in widget.winfo_children():
            self._leaga(copil, comanda)

    def _card_oprire(self, cheie, culoare_badge, text_badge, culoare_text_badge, titlu, subtitlu,
                     dreapta=None, sub_dreapta=None):
        """Un card din listă: număr în stânga, nume + detalii la mijloc, ora în dreapta."""
        card = ctk.CTkFrame(self.lista, corner_radius=12, fg_color=CARD, border_width=1, border_color=LINE)
        card.pack(fill="x", padx=(2, 2), pady=(0, 8))
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=text_badge, width=34, height=34, corner_radius=17, fg_color=culoare_badge,
                     text_color=culoare_text_badge, font=self.f(14, True)).grid(
            row=0, column=0, rowspan=2, padx=(12, 10), pady=12)
        ctk.CTkLabel(card, text=titlu, font=self.f(13, True), text_color=TEXT, anchor="w", justify="left",
                     wraplength=200).grid(row=0, column=1, sticky="w", pady=(12, 0))
        ctk.CTkLabel(card, text=subtitlu, font=self.f(11), text_color=MUTED, anchor="w").grid(
            row=1, column=1, sticky="w", pady=(0, 12))
        if dreapta:
            ctk.CTkLabel(card, text=dreapta, font=self.f(15, True), text_color=CIAN).grid(
                row=0, column=2, sticky="e", padx=(6, 14), pady=(12, 0))
            if sub_dreapta:
                ctk.CTkLabel(card, text=sub_dreapta, font=self.f(10), text_color=MUTED).grid(
                    row=1, column=2, sticky="e", padx=(6, 14), pady=(0, 12))
        try:
            card.configure(cursor="hand2")
        except Exception:
            pass
        self._leaga(card, lambda e, k=cheie: self.la_click_card(k))
        self.carduri[cheie] = card
        return card

    def _card_colet(self, i, colet):
        detalii = f"{colet[3]:g} kg · {colet[4]:g} m³ · {format_ora(colet[5])}–{format_ora(colet[6])}"
        self._card_oprire(i, AMBRA, str(i), "#1B1200", nume_scurt(colet[2], 60), detalii)

    def randeaza_opriri(self):
        """Reface toată lista de carduri."""
        for w in self.lista.winfo_children():
            w.destroy()
        self.carduri.clear()
        self._selectat = None

        if not self.depozit and not self.colete:
            self._lista_goala()
        elif self.rezultat:
            self._lista_traseu_optim()
        else:
            self._lista_colete()

    def _lista_goala(self):
        gol = ctk.CTkFrame(self.lista, fg_color="transparent")
        gol.pack(fill="x", pady=40)
        ctk.CTkLabel(gol, text="Nicio oprire încă", font=self.f(15, True), text_color=TEXT).pack()
        ctk.CTkLabel(gol, text="Adaugă prima adresă sau dă click pe hartă.\nPrima oprire devine depozitul.",
                     font=self.f(12), text_color=MUTED, justify="center").pack(pady=(6, 0))
        self.lbl_nr_opriri.configure(text="0 opriri")

    def _lista_colete(self):
        """Lista de dinainte de calcul: depozit + toate coletele (oricâte)."""
        if self.depozit:
            self._card_oprire("dep", INDIGO, "⌂", "#FFFFFF", nume_scurt(self.depozit[2], 60), "Punct de plecare")
        for i, colet in enumerate(self.colete, start=1):
            self._card_colet(i, colet)
        self.lbl_nr_opriri.configure(text=f"{len(self.colete)} colete")

    def _lista_traseu_optim(self):
        """Lista după calcul: plecare, opririle în ordine, sosire."""
        traseu, program = self.rezultat["traseu"], self.rezultat["program"]
        self._card_oprire("dep", INDIGO, "⌂", "#FFFFFF", nume_scurt(self.depozit[2], 60),
                          "Punct de plecare", format_ora(self.rezultat["plecare"]), "plecare")
        for pas in range(1, len(traseu) - 1):
            oprire = traseu[pas]
            ora, asteptare = program[pas - 1][0], program[pas - 1][1]
            detalii = f"{oprire[3]:g} kg · {oprire[4]:g} m³"
            text_asteptare = f"așteptare {asteptare:.0f} min" if asteptare >= 1 else "la timp"
            self._card_oprire(pas, OPRIRE, str(pas), "#FFFFFF", nume_scurt(oprire[2], 60), detalii,
                              format_ora(ora), text_asteptare)
        self._card_oprire("sosire", INDIGO, "⌂", "#FFFFFF", nume_scurt(self.depozit[2], 60), "Sosire în depozit")
        self.lbl_nr_opriri.configure(text=f"{len(traseu) - 2} opriri")

    def selecteaza_oprire(self, cheie, scroll=True):
        """Evidențiază cardul unei opriri (și îl aduce în vedere, dacă scroll=True)."""
        try:
            if self._selectat in self.carduri:
                self.carduri[self._selectat].configure(border_color=LINE, border_width=1, fg_color=CARD)
        except Exception:
            pass
        self._selectat = cheie
        card = self.carduri.get(cheie)
        if not card:
            return
        card.configure(border_color=CIAN, border_width=2, fg_color=CARD2)
        if scroll:
            try:
                self.update_idletasks()
                total = max(1, self.tab_traseu.winfo_height())
                y = self.lista.winfo_y() + card.winfo_y()
                self.tab_traseu._parent_canvas.yview_moveto(max(0.0, y / total - 0.02))
            except Exception:
                pass

    # ════════════════════ 6. STATISTICI ȘI PAȘI ════════════════════
    def reseteaza_kpi(self):
        for k in self.kpi.values():
            k.configure(text="—", text_color=TEXT)
        if self.colete:
            kg = round(sum(c[3] for c in self.colete), 3)
            m3 = round(sum(c[4] for c in self.colete), 3)
            self.lbl_incarcatura.configure(
                text=f"Încărcătură: {kg:g} kg · {m3:g} m³ · Calculează traseul pentru estimări.")
        else:
            self.lbl_incarcatura.configure(text="Estimările apar după calcularea traseului.")

    def seteaza_kpi(self, dist, eco, timp, cost):
        self.kpi["dist"].configure(text=dist)
        self.kpi["eco"].configure(text=eco, text_color=VERDE)
        self.kpi["timp"].configure(text=timp)
        self.kpi["cost"].configure(text=cost)

    def actualizeaza_pasi(self):
        """Bifează pașii făcuți și evidențiază pasul curent."""
        stari = [bool(self.depozit), bool(self.colete), self.rezultat is not None]
        activ = next((i for i, s in enumerate(stari) if not s), None)
        for i, (ch, badge, txt) in enumerate(self.chip_pasi):
            if stari[i]:
                badge.configure(text="✓", fg_color=VERDE, text_color="#052016")
                txt.configure(text_color=TEXT)
                ch.configure(border_color="#1F4D3F")
            elif i == activ:
                badge.configure(text=str(i + 1), fg_color=CIAN, text_color=INK)
                txt.configure(text_color=TEXT)
                ch.configure(border_color=CIAN)
            else:
                badge.configure(text=str(i + 1), fg_color=CARD2, text_color=MUTED)
                txt.configure(text_color=MUTED)
                ch.configure(border_color=LINE)

    def invalideaza_traseu(self):
        """Se apelează la orice modificare: șterge traseul vechi și reîmprospătează tot."""
        self.sterge_ruta()
        self.rezultat = None
        self.btn_calculeaza.configure(text=TXT_CALC)
        self.reseteaza_kpi()
        self.redesenare_markere()
        self.randeaza_opriri()
        self.actualizeaza_pasi()

    # ════════════════════ 7. CALCUL ÎN FUNDAL ════════════════════
    def _seteaza_ocupat(self, ocupat):
        """Afișează bara de progres și blochează butoanele cât timp lucrează ceva."""
        self._ocupat = ocupat
        if ocupat:
            self.bara.pack(fill="x", pady=(0, 10), before=self.btn_calculeaza)
            self.bara.start()
            self.btn_calculeaza.configure(state="disabled")
            self.btn_adauga.configure(state="disabled")
        else:
            self.bara.stop()
            self.bara.pack_forget()
            self.btn_calculeaza.configure(state="normal")
            self.btn_adauga.configure(state="normal")

    def _async(self, munca, la_succes, la_eroare):
        """Rulează `munca()` într-un fir separat (fereastra nu îngheață), apoi apelează
        `la_succes(rezultat)` sau `la_eroare(eroare)` în fereastra principală."""
        rezultat = {}

        def tinta():
            try:
                rezultat["ok"] = munca()
            except Exception as e:  # noqa: BLE001 - eroarea e arătată utilizatorului
                rezultat["err"] = e

        fir = threading.Thread(target=tinta, daemon=True)
        fir.start()

        def verifica():
            if fir.is_alive():
                self.after(80, verifica)
            elif "err" in rezultat:
                la_eroare(rezultat["err"])
            else:
                la_succes(rezultat["ok"])

        self.after(80, verifica)

    # ════════════════════ 8. ACȚIUNILE BUTOANELOR ════════════════════
    # ---- adăugare puncte ----
    def adauga_punct_hartas(self, lat, lon, nume, date=None, redesenare=True):
        """Primul punct e depozitul, următoarele sunt colete."""
        if self.depozit is None:
            self.depozit = [lat, lon, f"Depozit ({nume})"]
            self.seteaza_status("Depozit setat. Acum adaugă adresele coletelor.", "ok")
            if redesenare:
                self.invalideaza_traseu()
            return

        if date is None:
            try:
                date = date_colet(*(c.get() for c in self.campuri_colet))
            except ValueError as eroare:
                self.seteaza_status("Verifică datele coletului.", "err")
                messagebox.showerror("Date colet", str(eroare))
                return
        nr = len(self.colete) + 1
        self.colete.append([lat, lon, f"Colet {nr}: {nume}"] + date)
        self.seteaza_status(f"{nr} colete în listă. Calculează traseul când ești gata.", "ok")
        if not redesenare:
            return
        if self.rezultat is None:
            self._adauga_colet_rapid()      # doar elementul nou, nu refacem tot (rapid și la sute de colete)
        else:
            self.invalideaza_traseu()

    def _adauga_colet_rapid(self):
        i, colet = len(self.colete), self.colete[-1]
        self._pin_colet(i, colet)
        self._card_colet(i, colet)
        self.lbl_nr_opriri.configure(text=f"{i} colete")
        self.actualizeaza_pasi()
        self.reseteaza_kpi()

    def adauga_adresa_actiune(self):
        if self._ocupat:
            return
        text_adresa = self.camp_adresa.get().strip()
        if not text_adresa:
            return
        self.seteaza_status(f"Caut adresa: {text_adresa}…", "work")
        self._seteaza_ocupat(True)

        def gata(rezultat):
            self._seteaza_ocupat(False)
            if not rezultat:
                self.seteaza_status("Adresa nu a fost găsită. Încearcă cu oraș sau număr.", "err")
                return
            lat, lon, nume = rezultat[0], rezultat[1], rezultat[2]
            self.harta.set_position(lat, lon)
            self.harta.set_zoom(16)
            self.adauga_punct_hartas(lat, lon, nume)
            self.camp_adresa.delete(0, "end")

        def eroare(e):
            self._seteaza_ocupat(False)
            self.seteaza_status("Căutarea a eșuat. Verifică conexiunea la internet.", "err")

        self._async(lambda: gaseste_coordonate_adresa(text_adresa), gata, eroare)

    # ---- calcul traseu ----
    def calculeaza_traseu_actiune(self):
        if self._ocupat:
            return
        if not self.depozit or not self.colete:
            self.seteaza_status("Pune depozitul și minim un colet.", "warn")
            return
        try:
            plecare = ora_in_minute(self.camp_plecare.get())
        except ValueError as eroare:
            self.seteaza_status("Ora de plecare nu e validă.", "err")
            messagebox.showerror("Plecare", str(eroare))
            return

        self.invalideaza_traseu()
        self.seteaza_status("Calculez cel mai bun traseu pe străzi…", "work")
        self._seteaza_ocupat(True)
        depozit = list(self.depozit)
        colete = [list(c) for c in self.colete]

        def munca():
            traseu, km, km_neoptimizat, program = ruleaza_tsp_cheapest_insertion(depozit, colete, plecare)
            puncte = obtine_drum_pe_strazi(traseu)
            return traseu, km, km_neoptimizat, program, puncte

        def gata(rezultat):
            self._seteaza_ocupat(False)
            self._dupa_calcul(rezultat, plecare)

        def eroare(e):
            self._seteaza_ocupat(False)
            if isinstance(e, ValueError):
                self.seteaza_status("Nu s-a găsit un traseu valid.", "err")
                messagebox.showerror("Traseu", str(e))
            else:
                self.seteaza_status("Calculul a eșuat. Verifică conexiunea și încearcă din nou.", "err")
                messagebox.showerror("Traseu", f"{type(e).__name__}: {e}")

        self._async(munca, gata, eroare)

    def _dupa_calcul(self, rezultat, plecare):
        """Afișează traseul calculat: linie, pin-uri, listă, indicatori."""
        traseu_optim, km_optim, km_neoptimizat, program, puncte_sosea = rezultat
        economie = max(0.0, km_neoptimizat - km_optim)
        minute = int((km_optim / 35.0) * 60) + (len(self.colete) * 3) + sum(p[1] for p in program)
        cost_ron = ((km_optim * 8.0) / 100.0) * 7.5
        kg = sum(c[3] for c in self.colete)
        m3 = sum(c[4] for c in self.colete)
        stats = (f"Traseu AI: {km_optim:.2f} km (Economisit: {economie:.2f} km)\n"
                 f"Timp: ~{minute:.0f} min | Combustibil: {cost_ron:.2f} RON\n"
                 f"Total: {kg:g} kg | {m3:g} m³")

        self.rezultat = dict(traseu=traseu_optim, program=program, plecare=plecare, stats=stats)
        self.deseneaza_ruta(puncte_sosea)
        self.redesenare_markere()
        self.randeaza_opriri()
        self.actualizeaza_pasi()
        self.seteaza_kpi(f"{km_optim:.1f} km", f"{economie:.1f} km", fmt_timp(minute), f"{cost_ron:.1f} RON")
        self.lbl_incarcatura.configure(text=f"Încărcătură totală: {round(kg, 3):g} kg · {round(m3, 3):g} m³")
        self.btn_calculeaza.configure(text=TXT_RECALC)
        self.incadreaza_puncte([(p[0], p[1]) for p in traseu_optim])
        self.schimba_tab("Traseu")
        self.seteaza_status("Traseu optimizat. Click pe o oprire ca să o vezi pe hartă.", "ok")

    # ---- demo, import, export ----
    def incarca_demo(self):
        self.reseteaza_tot()
        demo = [
            (47.6533, 23.5514, "Depozit FAN Baia Mare"),
            (47.6593, 23.5818, "Str. Gheorghe Șincai 37"),
            (47.6472, 23.5691, "Vivo Mall Baia Mare"),
            (47.6661, 23.5679, "Spitalul Județean Baia Mare"),
            (47.6415, 23.5843, "Gara CFR Baia Mare"),
        ]
        for lat, lon, nume in demo:
            self.adauga_punct_hartas(lat, lon, nume, [2.0, 0.02, 480, 1080], redesenare=False)
        self.invalideaza_traseu()
        self.incadreaza_puncte([(d[0], d[1]) for d in demo])
        self.seteaza_status("Demo încărcat: 1 depozit și 4 colete. Apasă pe calculează.", "ok")

    def importa_csv(self):
        if self._ocupat:
            return
        if self.depozit is None:
            messagebox.showinfo("Import", "Adaugă mai întâi depozitul pe hartă.")
            return
        cale = filedialog.askopenfilename(filetypes=[("Listă colete", "*.csv")])
        if not cale:
            return
        self.seteaza_status("Import colete și căutare adrese…", "work")
        self._seteaza_ocupat(True)

        def gata(colete_noi):
            self._seteaza_ocupat(False)
            self.colete.extend(colete_noi)
            self.invalideaza_traseu()
            self.incadreaza_puncte([(self.depozit[0], self.depozit[1])] + [(c[0], c[1]) for c in self.colete])
            self.seteaza_status(f"Importate {len(colete_noi)} colete.", "ok")

        def eroare(e):
            self._seteaza_ocupat(False)
            self.seteaza_status("Importul nu a reușit.", "err")
            messagebox.showerror("Import nereușit", str(e))

        self._async(lambda: citeste_csv(cale, gaseste_coordonate_adresa), gata, eroare)

    def construieste_text(self):
        """Textul foii de parcurs, pentru export."""
        linii = ["=== FOAIE DE PARCURS - TRANSPORTER AI ===", ""]
        if self.rezultat:
            traseu, program = self.rezultat["traseu"], self.rezultat["program"]
            linii.append(f"0. PLECARE: {self.depozit[2]}")
            for pas in range(1, len(traseu) - 1):
                op = traseu[pas]
                linii.append(f"{pas}. {op[2]} | {op[3]:g} kg | {op[4]:g} m³")
                linii.append(f"   Livrare: {format_ora(program[pas - 1][0])}, așteptare {program[pas - 1][1]:.0f} min")
            linii.append(f"{len(traseu) - 1}. SOSIRE: {self.depozit[2]}")
            linii += ["", self.rezultat["stats"]]
        else:
            linii.append(f"START: {self.depozit[2]}")
            for c in self.colete:
                linii.append(f"  • {c[2]} | {c[3]:g} kg | {c[4]:g} m³ | {format_ora(c[5])}–{format_ora(c[6])}")
        return "\n".join(linii) + "\n"

    def salveaza_txt(self):
        if not self.depozit:
            messagebox.showinfo("Export", "Nu există nimic de salvat încă.")
            return
        cale = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="foaie_parcurs_transporter.txt",
                                            filetypes=[("Text", "*.txt")])
        if not cale:
            return
        with open(cale, "w", encoding="utf-8") as f:
            f.write(self.construieste_text())
        self.seteaza_status(f"Foaia de parcurs a fost salvată: {cale}", "ok")

    # ---- ștergere ----
    def sterge_ultimul(self):
        if self._ocupat:
            return
        if self.colete:
            self.colete.pop()
            self.invalideaza_traseu()
            self.seteaza_status("Ultimul colet a fost șters.", "info")
        elif self.depozit:
            self.depozit = None
            self.invalideaza_traseu()
            self.seteaza_status("Setează depozitul: scrie o adresă sau dă click pe hartă.", "info")

    def reseteaza_tot(self):
        if self._ocupat:
            return
        self.depozit = None
        self.colete.clear()
        self.invalideaza_traseu()
        self.schimba_tab("Planificare")
        self.seteaza_status("Totul a fost resetat. Setează depozitul pentru a începe.", "info")


if __name__ == "__main__":
    FereastraCurier().mainloop()
