import streamlit as st
import numpy_financial as npf
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import io

st.set_page_config(page_title="Simulatore Finanziario Professionale", layout="wide")

# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_professionale(df, rata, capitale, mesi, tan):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    data_header = [
        ["Riepilogo Finanziamento", ""],
        ["Capitale Finanziato", f"{capitale:.2f} €"],
        ["Durata", f"{mesi} mesi"],
        ["TAN", f"{tan:.2f} %"],
        ["Rata Mensile", f"{rata:.2f} €"]
    ]
    t_header = Table(data_header)
    t_header.setStyle(TableStyle([('BACKGROUND', (0, 0), (1, 0), colors.grey),
                                  ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                                  ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                  ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                                  ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]))
    elements.append(t_header)
    
    data_piano = [["Mese", "Rata", "Quota Int.", "Quota Cap.", "Residuo"]]
    for index, row in df.iterrows():
        data_piano.append([
            int(row['Mese']),
            f"{row['Rata']:.2f}",
            f"{row['Quota Interessi']:.2f}",
            f"{row['Quota Capitale']:.2f}",
            f"{row['Debito Residuo']:.2f}"
        ])
    
    t_piano = Table(data_piano, repeatRows=1)
    t_piano.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                                 ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                 ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                 ('FONTSIZE', (0, 0), (-1, -1), 9)]))
    elements.append(t_piano)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- INTERFACCIA ---
st.title("🏦 Portale Simulazione Finanziaria")
st.markdown("---")

# SEZIONE 1: INPUT E RISULTATI IMMEDIATI (FRONT-END)
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    capitale = st.number_input("Capitale Finanziato (€)", value=10000, step=500)
    mesi = st.number_input("Durata (Mesi)", value=54, step=6)
    # STEP TAN: 0.05%
    tan = st.number_input("TAN (%)", value=7.95, step=0.05, format="%.2f")

with col2:
    # STEP ISTRUTTORIA: 10€
    istruttoria_cli = st.number_input("Istruttoria Cliente (€)", value=0, step=10)
    # STEP INCASSO RATA: 0.10€
    spese_m = st.number_input("Incasso Rata Mensile (€)", value=3.00, step=0.10, format="%.2f")
    bollo_i = st.number_input("Bollo 1° Rata (€)", value=16.0, step=1.0)

# Calcoli Rata e TAEG
i_m = (tan / 100) / 12
rata_teorica = npf.pmt(i_m, mesi, -capitale)
rata_reale = round(rata_teorica, 0)
esborso_cli = capitale - istruttoria_cli - bollo_i
flussi_taeg = [-esborso_cli] + [rata_reale + spese_m] * mesi
taeg_val = ((1 + npf.irr(flussi_taeg)) ** 12 - 1) * 100

with col3:
    st.subheader("Risultati Cliente")
    st.metric("RATA MENSILE (€)", f"{rata_reale:.2f}")
    st.metric("TAEG (%)", f"{taeg_val:.3f}")

st.markdown("---")

# SEZIONE 2: PIANO AMMORTAMENTO
st.subheader("🗓️ Piano di Ammortamento")
data_amm = []
residuo = capitale
for m in range(1, mesi + 1):
    q_int = residuo * i_m
    q_cap = rata_reale - q_int
    residuo -= q_cap
    data_amm.append([m, rata_reale, q_int, q_cap, max(0, residuo)])

df_amm = pd.DataFrame(data_amm, columns=['Mese', 'Rata', 'Quota Interessi', 'Quota Capitale', 'Debito Residuo'])

with st.expander("Visualizza Tabella Dettagliata"):
    st.dataframe(df_amm, use_container_width=True)
    pdf_file = genera_pdf_professionale(df_amm, rata_reale, capitale, mesi, tan)
    st.download_button("📩 Scarica Piano in PDF", data=pdf_file, file_name="piano_ammortamento.pdf", mime="application/pdf")

st.markdown("---")

# SEZIONE 3: ASPETTO TECNICO (BACK-END)
st.subheader("⚙️ Back-End Tecnico (Redditività)")
col_t1, col_t2 = st.columns(2)

# Logica di calcolo nascosta
monte_int = (rata_reale * mesi) - capitale
imp_sost = capitale * 0.0025

with col_t1:
    st.write("**Dettaglio Provvigioni**")
    p_agente_p = st.number_input("% Agente", value=0.70, step=0.05, format="%.2f")
    # STEP DEALER: 1%
    p_dealer_p = st.number_input("% Dealer (su Monte Int.)", value=13.00, step=1.00, format="%.2f")
    
    c_dealer = monte_int * (p_dealer_p / 100)
    c_agente = capitale * (p_agente_p / 100)

with col_t2:
    st.write("**Rendimento Banca**")
    esborso_banca = -capitale - c_dealer - c_agente - imp_sost + istruttoria_cli
    flussi_irr = [esborso_banca] + [rata_reale] * mesi
    irr_annuo = ((1 + npf.irr(flussi_irr)) ** 12 - 1) * 100
    
    st.metric("IRR BANCA (TIR)", f"{irr_annuo:.3f} %")
    st.write(f"• Provvigione Dealer: **{c_dealer:.2f} €**")
    st.write(f"• Provvigione Agente: **{c_agente:.2f} €**")
    # --- FIRMA IN BASSO ---
st.markdown("---")
st.markdown(
    """
    <style>
    .footer {
        position: relative;
        left: 0;
        bottom: 0;
        width: 100%;
        color: #888888;
        text-align: center;
        padding: 20px;
        font-size: 14px;
        font-style: italic;
    }
    </style>
    <div class="footer">
        Made with ❤️ by NC Finservice
    </div>
    """,
    unsafe_allow_html=True
)