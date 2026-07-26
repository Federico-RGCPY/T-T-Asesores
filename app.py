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
    page_title="T&T Asesores — Gestión de Banco y Facturación",
    page_icon="💼",
    layout="wide"
)

# ID DE TU GOOGLE SHEET (Crea una planilla nativa de Google y pega su ID aquí)
SPREADSHEET_ID = "REEMPLAZA_CON_EL_ID_DE_TU_NUEVO_GOOGLE_SHEET"

# Estilos CSS
st.markdown(
    """
    <style>
    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .header-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #1e293b;
        margin: 0;
    }
    .metric-card {
        background-color: #ffffff;
        border-left: 5px solid #0284c7;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 2. ENCABEZADO CON LOGO
# -----------------------------------------------------------------------------
col_logo, col_tit = st.columns([1, 4])

with col_logo:
    # URL de la imagen del Logo T&T Asesores
    LOGO_URL = "https://instagram.fcl1-1.fna.fbcdn.net/v/t51.2885-15/403698047_1018318296095945_1907530669174092770_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=170069&_nc_ohc=logo"
    try:
        st.image("https://raw.githubusercontent.com/streamlit/streamlit/main/docs/static/logo.png", width=120) # Reemplazar URL pública si la de Instagram caduca
    except Exception:
        st.title("💼 T&T")

with col_tit:
    st.markdown("<h1 class='header-title'>T&T Asesores</h1>", unsafe_allow_html=True)
    st.caption("Sistema de Control Bancario, Facturación Emitida y Estado de Cuentas (USD $)")

st.markdown("---")

# -----------------------------------------------------------------------------
# 3. CONEXIÓN Y FUNCIONES DE GOOGLE SHEETS
# -----------------------------------------------------------------------------
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

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
        return None, "Falta la configuración de credenciales en Secrets."

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
# 4. MENÚ NAVEGACIÓN
# -----------------------------------------------------------------------------
menu = st.radio(
    "Navegación:",
    ["📊 Resumen de Bancos (USD)", "📄 Facturas Emitidas", "💳 Registro de Movimientos", "⚙️ Configuración Saldos Iniciales"],
    horizontal=True
)

st.markdown("---")

# =============================================================================
# MÓDULO 1: RESUMEN DE BANCOS Y SALDOS
# =============================================================================
if menu == "📊 Resumen de Bancos (USD)":
    st.subheader("🏦 Estado de Cuenta de Bancos (USD)")

    df_config = obtener_datos("Config_Bancos")
    df_mov = obtener_datos("Movimientos_Banco")

    saldos = {"Bice": 0.0, "Falabella": 0.0}

    # Cargar Saldos Iniciales
    if not df_config.empty and "Banco" in df_config.columns and "Saldo_Inicial_USD" in df_config.columns:
        for _, r in df_config.iterrows():
            b_nom = r.get("Banco")
            if b_nom in saldos:
                try:
                    saldos[b_nom] = float(r.get("Saldo_Inicial_USD", 0))
                except Exception:
                    pass

    # Sumar Movimientos
    ingresos_bice = 0.0
    egresos_bice = 0.0
    ingresos_fala = 0.0
    egresos_fala = 0.0

    if not df_mov.empty and "Banco" in df_mov.columns:
        for _, r in df_mov.iterrows():
            b = str(r.get("Banco", "")).strip()
            tipo = str(r.get("Tipo", "")).strip()
            try:
                monto = float(r.get("Monto_USD", 0))
            except Exception:
                monto = 0.0

            if b == "Bice":
                if tipo == "Ingreso": ingresos_bice += monto
                else: egresos_bice += monto
            elif b == "Falabella":
                if tipo == "Ingreso": ingresos_fala += monto
                else: egresos_fala += monto

    saldo_final_bice = saldos["Bice"] + ingresos_bice - egresos_bice
    saldo_final_fala = saldos["Falabella"] + ingresos_fala - egresos_fala

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🏦 Banco BICE", f"${saldo_final_bice:,.2f} USD", f"Inicial: ${saldos['Bice']:,.2f}")
    with c2:
        st.metric("💳 Banco Falabella", f"${saldo_final_fala:,.2f} USD", f"Inicial: ${saldos['Falabella']:,.2f}")
    with c3:
        st.metric("💰 Total Disponible", f"${(saldo_final_bice + saldo_final_fala):,.2f} USD")

    st.markdown("### 📋 ÚLTIMOS MOVIMIENTOS BANCARIOS")
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
        with st.form("form_factura"):
            f_cli = st.text_input("Nombre del Cliente *")
            f_monto = st.number_input("Monto Total (USD) *", min_value=0.01, step=10.0)
            f_fecha = st.date_input("Fecha de Emisión", value=date.today())
            
            sub_fact = st.form_submit_button("💾 Guardar Factura")
            if sub_fact:
                if not f_cli:
                    st.error("Ingresa el nombre del cliente.")
                else:
                    new_id = f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    datos_fac = [new_id, f_cli.strip(), f_monto, str(f_fecha), "Pendiente", 0.0, f_monto]
                    ok, err = agregar_fila("Facturas", datos_fac)
                    if ok:
                        st.success("Factura registrada exitosamente.")
                        st.rerun()
                    else:
                        st.error(f"Error: {err}")

    st.markdown("### 📚 Facturas en Sistema")
    df_fac = obtener_datos("Facturas")
    if not df_fac.empty:
        st.dataframe(df_fac, use_container_width=True)
    else:
        st.info("No hay facturas registradas.")

# =============================================================================
# MÓDULO 3: REGISTRO DE MOVIMIENTOS (INGRESOS Y EGRESOS)
# =============================================================================
elif menu == "💳 Registro de Movimientos":
    st.subheader("💸 Registrar Movimiento Bancario (Ingreso / Egreso)")

    with st.form("form_movimiento"):
        cm1, cm2, cm3 = st.columns(3)
        with cm1:
            banco_sel = st.selectbox("Banco *", ["Bice", "Falabella"])
        with cm2:
            tipo_mov = st.selectbox("Tipo de Movimiento *", ["Ingreso", "Egreso"])
        with cm3:
            monto_mov = st.number_input("Monto (USD) *", min_value=0.01, step=10.0)

        cm4, cm5 = st.columns(2)
        with cm4:
            fecha_mov = st.date_input("Fecha", value=date.today())
        with cm5:
            cliente_mov = st.text_input("Cliente / Proveedor Asociado")

        detalle_mov = st.text_area("Detalle / Glosa del Movimiento")

        sub_mov = st.form_submit_button("💾 Registrar Movimiento en Banco")

        if sub_mov:
            id_m = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            registro_mov = [id_m, banco_sel, tipo_mov, monto_mov, str(fecha_mov), cliente_mov.strip(), detalle_mov.strip()]
            ok, err = agregar_fila("Movimientos_Banco", registro_mov)
            if ok:
                st.success("Movimiento registrado con éxito.")
                st.rerun()
            else:
                st.error(f"Error: {err}")

# =============================================================================
# MÓDULO 4: CONFIGURACIÓN DE SALDOS INICIALES
# =============================================================================
elif menu == "⚙️ Configuración Saldos Iniciales":
    st.subheader("⚙️ Configurar Saldo Inicial de los Bancos")

    with st.form("form_saldos_ini"):
        s_bice = st.number_input("Saldo Inicial Banco BICE (USD)", min_value=0.0, step=100.0)
        s_fala = st.number_input("Saldo Inicial Banco Falabella (USD)", min_value=0.0, step=100.0)

        sub_ini = st.form_submit_button("💾 Actualizar Saldos Iniciales")

        if sub_ini:
            ok1, _ = agregar_fila("Config_Bancos", ["Bice", s_bice])
            ok2, _ = agregar_fila("Config_Bancos", ["Falabella", s_fala])
            if ok1 and ok2:
                st.success("Saldos iniciales actualizados correctamente.")
                st.rerun()
