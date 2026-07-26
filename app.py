import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="T&T Asesores — Control Bancario & Facturación",
    page_icon="💼",
    layout="wide"
)

# 🔑 ID DE TU GOOGLE SHEET NATIVO
SPREADSHEET_ID = "1yUoPjGAIvcDr08xMq0VhR6cOj2TP6c2eUfuPrLNkFy4"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');
    .stApp { background-color: #f8fafc; }
    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .header-title {
        font-family: 'Montserrat', sans-serif;
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0;
        color: #ffffff;
    }
    .header-sub {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-top: 5px;
    }
    .metric-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #0284c7;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 2. ENCABEZADO T&T ASESORES
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class='header-box'>
        <div class='header-title'>T&T ASESORES</div>
        <div class='header-sub'>Control Financiero, Movimientos Bancarios y Facturación (USD $)</div>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 3. CONEXIÓN Y OPERACIONES EN GOOGLE SHEETS
# -----------------------------------------------------------------------------
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar_sheet():
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "gcp_json" in st.secrets:
        try:
            creds_dict = json.loads(str(st.secrets["gcp_json"]).strip("'\""), strict=False)
        except Exception:
            pass

    if not creds_dict:
        return None, "Falta configurar las credenciales de Google en Secrets."

    try:
        pk = creds_dict.get("private_key", "")
        if "\\n" in pk:
            creds_dict["private_key"] = pk.replace("\\n", "\n")

        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        return sh, None
    except Exception as e:
        return None, str(e)

def obtener_datos(pestana_nombre):
    sh, err = conectar_sheet()
    if sh:
        try:
            ws = sh.worksheet(pestana_nombre)
            vals = ws.get_all_values()
            if len(vals) > 1:
                headers = [str(h).strip() for h in vals[0]]
                data = vals[1:]
                return pd.DataFrame(data, columns=headers)
        except Exception:
            pass
    return pd.DataFrame()

def agregar_fila(pestana_nombre, fila_datos):
    sh, err = conectar_sheet()
    if sh:
        try:
            ws = sh.worksheet(pestana_nombre)
            ws.append_row([str(x) for x in fila_datos], value_input_option="USER_ENTERED")
            return True, None
        except Exception as e:
            return False, str(e)
    return False, err

# -----------------------------------------------------------------------------
# 4. MENÚ PRINCIPAL
# -----------------------------------------------------------------------------
menu = st.radio(
    "Navegación:",
    ["📊 Resumen de Bancos (USD)", "📄 Facturas Emitidas", "💳 Movimientos Bancarios", "⚙️ Configurar Saldos Iniciales"],
    horizontal=True
)

st.markdown("---")

# Comprobación inicial de conexión
sh_test, err_test = conectar_sheet()
if not sh_test:
    st.warning(f"⚠️ **Atención:** No hay conexión con Google Sheets. Motivo: `{err_test}`")

# =============================================================================
# MÓDULO 1: RESUMEN DE BANCOS (BICE Y FALABELLA)
# =============================================================================
if menu == "📊 Resumen de Bancos (USD)":
    st.subheader("🏦 Estado de Cuentas Bancarias")

    df_config = obtener_datos("Config_Bancos")
    df_mov = obtener_datos("Movimientos_Banco")

    saldo_ini_bice = 0.0
    saldo_ini_fala = 0.0

    if not df_config.empty:
        for _, r in df_config.iterrows():
            b_nom = str(r.get("Banco", "")).strip().lower()
            try:
                m_val = float(r.get("Saldo_Inicial_USD", 0))
            except Exception:
                m_val = 0.0

            if "bice" in b_nom:
                saldo_ini_bice = m_val
            elif "falabella" in b_nom:
                saldo_ini_fala = m_val

    ingresos_bice, egresos_bice = 0.0, 0.0
    ingresos_fala, egresos_fala = 0.0, 0.0

    if not df_mov.empty:
        for _, r in df_mov.iterrows():
            b = str(r.get("Banco", "")).strip().lower()
            tipo = str(r.get("Tipo", "")).strip().lower()
            try:
                monto = float(r.get("Monto_USD", 0))
            except Exception:
                monto = 0.0

            if "bice" in b:
                if "ingreso" in tipo: ingresos_bice += monto
                else: egresos_bice += monto
            elif "falabella" in b:
                if "ingreso" in tipo: ingresos_fala += monto
                else: egresos_fala += monto

    saldo_fin_bice = saldo_ini_bice + ingresos_bice - egresos_bice
    saldo_fin_fala = saldo_ini_fala + ingresos_fala - egresos_fala

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🏦 Banco BICE", f"${saldo_fin_bice:,.2f} USD", delta=f"Inicial: ${saldo_ini_bice:,.2f}")
    with c2:
        st.metric("💳 Banco Falabella", f"${saldo_fin_fala:,.2f} USD", delta=f"Inicial: ${saldo_ini_fala:,.2f}")
    with c3:
        st.metric("💰 Total Disponible", f"${(saldo_fin_bice + saldo_fin_fala):,.2f} USD")

    st.markdown("### 📋 Historial de Movimientos")
    if not df_mov.empty:
        st.dataframe(df_mov, use_container_width=True)
    else:
        st.info("No hay movimientos registrados en el banco.")

# =============================================================================
# MÓDULO 2: FACTURAS EMITIDAS
# =============================================================================
elif menu == "📄 Facturas Emitidas":
    st.subheader("📄 Registro de Facturas Emitidas")

    with st.expander("➕ Emitir Nueva Factura", expanded=False):
        with st.form("form_factura", clear_on_submit=True):
            f_cli = st.text_input("Cliente *", placeholder="Ej: Empresa ABC SpA")
            f_monto = st.number_input("Monto Total (USD) *", min_value=0.01, step=50.0)
            f_fecha = st.date_input("Fecha de Emisión", value=date.today())

            sub_fact = st.form_submit_button("💾 Guardar Factura")
            if sub_fact:
                if not f_cli:
                    st.error("Debes ingresar el nombre del cliente.")
                else:
                    new_id = f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    datos_fac = [new_id, f_cli.strip(), f_monto, str(f_fecha), "Pendiente", 0.0, f_monto]
                    ok, err = agregar_fila("Facturas", datos_fac)
                    if ok:
                        st.success("Factura registrada correctamente.")
                        st.rerun()
                    else:
                        st.error(f"Error al guardar: {err}")

    st.markdown("### 📚 Facturas Registradas")
    df_fac = obtener_datos("Facturas")
    if not df_fac.empty:
        st.dataframe(df_fac, use_container_width=True)
    else:
        st.info("No hay facturas emitidas.")

# =============================================================================
# MÓDULO 3: REGISTRO DE MOVIMIENTOS
# =============================================================================
elif menu == "💳 Movimientos Bancarios":
    st.subheader("💸 Registrar Movimiento de Banco")

    with st.form("form_movimiento", clear_on_submit=True):
        cm1, cm2, cm3 = st.columns(3)
        with cm1:
            banco_sel = st.selectbox("Banco *", ["Bice", "Falabella"])
        with cm2:
            tipo_mov = st.selectbox("Tipo *", ["Ingreso", "Egreso"])
        with cm3:
            monto_mov = st.number_input("Monto (USD) *", min_value=0.01, step=50.0)

        cm4, cm5 = st.columns(2)
        with cm4:
            fecha_mov = st.date_input("Fecha", value=date.today())
        with cm5:
            cliente_mov = st.text_input("Cliente / Proveedor")

        detalle_mov = st.text_area("Detalle / Observaciones")

        sub_mov = st.form_submit_button("💾 Registrar Movimiento")
        if sub_mov:
            id_m = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            registro_mov = [id_m, banco_sel, tipo_mov, monto_mov, str(fecha_mov), cliente_mov.strip(), detalle_mov.strip()]
            ok, err = agregar_fila("Movimientos_Banco", registro_mov)
            if ok:
                st.success("Movimiento registrado en el banco.")
                st.rerun()
            else:
                st.error(f"Error: {err}")

# =============================================================================
# MÓDULO 4: SALDOS INICIALES
# =============================================================================
elif menu == "⚙️ Configurar Saldos Iniciales":
    st.subheader("⚙️ Definir Saldos Iniciales en Bancos (USD)")

    with st.form("form_saldos_ini"):
        s_bice = st.number_input("Saldo Inicial BICE (USD)", min_value=0.0, step=500.0)
        s_fala = st.number_input("Saldo Inicial Falabella (USD)", min_value=0.0, step=500.0)

        sub_ini = st.form_submit_button("💾 Guardar Saldos Iniciales")
        if sub_ini:
            ok1, _ = agregar_fila("Config_Bancos", ["Bice", s_bice])
            ok2, _ = agregar_fila("Config_Bancos", ["Falabella", s_fala])
            if ok1 and ok2:
                st.success("Saldos iniciales guardados.")
                st.rerun()
            else:
                st.error("Error al guardar saldos iniciales.")
