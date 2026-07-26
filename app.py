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

def limpiar_key(texto):
    replacements = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"))
    s = str(texto).lower().strip()
    for a, b in replacements:
        s = s.replace(a, b)
    return s

def obtener_datos(pestana_nombre):
    sh, err = conectar_sheet()
    if sh:
        try:
            ws = sh.worksheet(pestana_nombre)
            vals = ws.get_all_values()
            if len(vals) >= 1:
                headers_raw = [str(h).strip() for h in vals[0]]
                data = vals[1:]
                rows_clean = []
                for idx, r in enumerate(data):
                    if not any(r):
                        continue
                    row_dict = {}
                    for c_idx, val in enumerate(r):
                        row_dict[f"col_{c_idx}"] = val
                        if c_idx < len(headers_raw):
                            clean_k = limpiar_key(headers_raw[c_idx])
                            row_dict[clean_k] = val
                            row_dict[headers_raw[c_idx]] = val
                    row_dict["_fila_num"] = idx + 2
                    rows_clean.append(row_dict)
                return pd.DataFrame(rows_clean)
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

def actualizar_fila(pestana_nombre, fila_num, datos_actualizados):
    sh, err = conectar_sheet()
    if sh:
        try:
            ws = sh.worksheet(pestana_nombre)
            num_cols = len(datos_actualizados)
            col_letra = chr(64 + num_cols) if num_cols <= 26 else "G"
            rango = f"A{fila_num}:{col_letra}{fila_num}"
            ws.update(rango, [[str(x) for x in datos_actualizados]], value_input_option="USER_ENTERED")
            return True, None
        except Exception as e:
            return False, str(e)
    return False, err

def eliminar_fila(pestana_nombre, fila_num):
    sh, err = conectar_sheet()
    if sh:
        try:
            ws = sh.worksheet(pestana_nombre)
            ws.delete_rows(int(fila_num))
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

sh_test, err_test = conectar_sheet()
if not sh_test:
    st.warning(f"⚠️ **Atención:** No hay conexión con Google Sheets. Motivo: `{err_test}`")

# =============================================================================
# MÓDULO 1: RESUMEN DE BANCOS Y DISPONIBILIDAD TOTAL
# =============================================================================
if menu == "📊 Resumen de Bancos (USD)":
    st.subheader("🏦 Estado de Cuentas Bancarias y Disponibilidad Total")

    df_config = obtener_datos("Config_Bancos")
    df_mov = obtener_datos("Movimientos_Banco")
    df_fac = obtener_datos("Facturas")

    saldo_ini_bice = 0.0
    saldo_ini_fala = 0.0

    if not df_config.empty:
        for _, r in df_config.iterrows():
            b_nom = str(r.get("banco", r.get("col_0", ""))).strip().lower()
            try:
                m_val = float(r.get("saldo_inicial_usd", r.get("col_1", 0)))
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
            b = str(r.get("banco", r.get("col_1", ""))).strip().lower()
            tipo = str(r.get("tipo", r.get("col_2", ""))).strip().lower()
            try:
                monto = float(r.get("monto_usd", r.get("col_3", 0)))
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

    # Cálculos de Facturación
    total_facturado = 0.0
    total_cobrado = 0.0
    total_pendiente = 0.0

    if not df_fac.empty:
        for _, r in df_fac.iterrows():
            try:
                m_tot = float(r.get("monto_usd", r.get("col_2", 0)))
            except Exception:
                m_tot = 0.0
            try:
                m_pag = float(r.get("monto_pagado", r.get("col_5", 0)))
            except Exception:
                m_pag = 0.0
            try:
                m_pend = float(r.get("saldo_pendiente", r.get("col_6", m_tot - m_pag)))
            except Exception:
                m_pend = max(0.0, m_tot - m_pag)

            total_facturado += m_tot
            total_cobrado += m_pag
            total_pendiente += m_pend

    # Disponibilidad Total = Suma Bancos + Facturas Pendientes de Pago
    disponibilidad_total = saldo_fin_bice + saldo_fin_fala + total_pendiente

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("🏦 Banco BICE", f"${saldo_fin_bice:,.2f} USD", delta=f"Inicial: ${saldo_ini_bice:,.2f}")
    with c2:
        st.metric("💳 Banco Falabella", f"${saldo_fin_fala:,.2f} USD", delta=f"Inicial: ${saldo_ini_fala:,.2f}")
    with c3:
        st.metric("📄 Total Facturado", f"${total_facturado:,.2f} USD", help="Monto total emitido en facturas")
    with c4:
        st.metric("⏳ Facturas Pendientes", f"${total_pendiente:,.2f} USD", delta=f"Cobrado: ${total_cobrado:,.2f}", delta_color="normal")
    with c5:
        st.metric("💰 Disponibilidad Total", f"${disponibilidad_total:,.2f} USD", help="Suma de Bancos + Facturas Pendientes de Pago")

    st.markdown("---")
    st.markdown("### 📋 Historial de Movimientos Bancarios")
    if not df_mov.empty:
        st.dataframe(df_mov, use_container_width=True)
    else:
        st.info("No hay movimientos registrados en los bancos.")

# =============================================================================
# MÓDULO 2: FACTURAS EMITIDAS (CON REGISTRO AUTOMÁTICO EN BANCO)
# =============================================================================
elif menu == "📄 Facturas Emitidas":
    st.subheader("📄 Registro y Gestión de Facturas Emitidas")

    with st.expander("➕ Emitir Nueva Factura", expanded=False):
        with st.form("form_factura", clear_on_submit=True):
            f_cli = st.text_input("Cliente *", placeholder="Ej: Empresa ABC SpA")
            f_monto = st.number_input("Monto Total (USD) *", min_value=0.01, step=50.0)
            f_fecha = st.date_input("Fecha de Emisión", value=date.today())
            f_estado = st.selectbox("Estado Inicial", ["Pendiente", "Pagado"])
            banco_destino = st.selectbox("Si está Pagada, ¿a qué Banco ingresa?", ["Bice", "Falabella"])

            sub_fact = st.form_submit_button("💾 Guardar Factura")
            if sub_fact:
                if not f_cli:
                    st.error("Debes ingresar el nombre del cliente.")
                else:
                    new_id = f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    m_pagado = f_monto if f_estado == "Pagado" else 0.0
                    s_pendiente = 0.0 if f_estado == "Pagado" else f_monto
                    datos_fac = [new_id, f_cli.strip(), f_monto, str(f_fecha), f_estado, m_pagado, s_pendiente]
                    ok, err = agregar_fila("Facturas", datos_fac)
                    
                    if ok:
                        # Si nace pagada, volcar automáticamente como Ingreso en Banco
                        if f_estado == "Pagado":
                            id_m = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            reg_mov = [id_m, banco_destino, "Ingreso", f_monto, str(f_fecha), f_cli.strip(), f"Pago de Factura {new_id}"]
                            agregar_fila("Movimientos_Banco", reg_mov)
                        st.success("Factura registrada correctamente.")
                        st.rerun()
                    else:
                        st.error(f"Error al guardar: {err}")

    st.markdown("### 📚 Listado de Facturas Emitidas")
    df_fac = obtener_datos("Facturas")

    if not df_fac.empty:
        for idx, r in df_fac.iterrows():
            id_f = str(r.get("id_factura", r.get("col_0", "")))
            cli_f = str(r.get("cliente", r.get("col_1", "")))
            try:
                monto_f = float(r.get("monto_usd", r.get("col_2", 0)))
            except Exception:
                monto_f = 0.0
            fecha_f = str(r.get("fecha_emision", r.get("col_3", "")))
            estado_f = str(r.get("estado", r.get("col_4", "Pendiente")))
            try:
                pagado_f = float(r.get("monto_pagado", r.get("col_5", 0)))
            except Exception:
                pagado_f = 0.0
            try:
                saldo_f = float(r.get("saldo_pendiente", r.get("col_6", monto_f)))
            except Exception:
                saldo_f = monto_f
            fila_num = r.get("_fila_num")

            col_info, col_acc = st.columns([0.8, 0.2])

            with col_info:
                st.markdown(
                    f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; border-left: 5px solid {'#22c55e' if estado_f == 'Pagado' else '#f59e0b'}; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                        <b>{id_f}</b> | 👤 <b>Cliente:</b> {cli_f} | 📅 <b>Fecha:</b> {fecha_f}<br>
                        💵 <b>Monto Facturado:</b> ${monto_f:,.2f} USD | 🟢 <b>Cobrado en Banco:</b> ${pagado_f:,.2f} USD | ⏳ <b>Pendiente de Pago:</b> ${saldo_f:,.2f} USD | <b>Estado:</b> {estado_f}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col_acc:
                ca1, ca2 = st.columns(2)
                with ca1:
                    if st.button("✏️", key=f"edit_fac_{fila_num}_{idx}", help="Editar / Cobrar Factura"):
                        st.session_state[f"edit_fac_mode_{fila_num}"] = not st.session_state.get(f"edit_fac_mode_{fila_num}", False)
                with ca2:
                    if st.button("❌", key=f"del_fac_{fila_num}_{idx}", help="Eliminar Factura"):
                        ok_del, err_del = eliminar_fila("Facturas", fila_num)
                        if ok_del:
                            st.success("Factura eliminada.")
                            st.rerun()
                        else:
                            st.error(f"Error borrando: {err_del}")

            # Modal de edición y cobro
            if st.session_state.get(f"edit_fac_mode_{fila_num}", False):
                with st.container():
                    st.info(f"✏️ **Editando / Registrar Cobro de Factura:** {id_f}")
                    with st.form(f"form_edit_fac_{fila_num}"):
                        fe1, fe2 = st.columns(2)
                        with fe1:
                            cli_edit = st.text_input("Cliente", value=cli_f, key=f"cli_e_{fila_num}")
                            monto_edit = st.number_input("Monto Total (USD)", value=monto_f, min_value=0.01, step=50.0, key=f"m_e_{fila_num}")
                        with fe2:
                            try:
                                default_dt = pd.to_datetime(fecha_f).date()
                            except Exception:
                                default_dt = date.today()
                            fecha_edit = st.date_input("Fecha Emisión", value=default_dt, key=f"f_e_{fila_num}")
                            estado_edit = st.selectbox("Estado de Pago", ["Pendiente", "Pagado"], index=0 if estado_f == "Pendiente" else 1, key=f"est_e_{fila_num}")

                        pagado_edit = st.number_input("Monto Cobrado que ingresa al Banco (USD)", value=(monto_edit if estado_edit == "Pagado" else pagado_f), min_value=0.0, max_value=monto_edit, key=f"pag_e_{fila_num}")
                        banco_cobro = st.selectbox("Banco donde se deposita el cobro", ["Bice", "Falabella"], key=f"bco_e_{fila_num}")

                        btn_save_fac = st.form_submit_button("💾 Guardar y Actualizar Banco")

                        if btn_save_fac:
                            saldo_calc = max(0.0, monto_edit - pagado_edit)
                            estado_final = "Pagado" if saldo_calc == 0.0 else estado_edit
                            
                            datos_act = [
                                id_f,
                                cli_edit.strip(),
                                monto_edit,
                                str(fecha_edit),
                                estado_final,
                                pagado_edit,
                                saldo_calc
                            ]
                            ok_upd, err_upd = actualizar_fila("Facturas", fila_num, datos_act)
                            
                            if ok_upd:
                                # Registrar la diferencia cobrada en el historial bancario
                                diferencia_cobrada = pagado_edit - pagado_f
                                if diferencia_cobrada > 0:
                                    id_m = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                    reg_mov = [id_m, banco_cobro, "Ingreso", diferencia_cobrada, str(date.today()), cli_edit.strip(), f"Abono / Pago de Factura {id_f}"]
                                    agregar_fila("Movimientos_Banco", reg_mov)

                                st.success("Factura y movimientos de banco actualizados correctamente.")
                                st.session_state[f"edit_fac_mode_{fila_num}"] = False
                                st.rerun()
                            else:
                                st.error(f"Error al actualizar: {err_upd}")
    else:
        st.info("No hay facturas emitidas.")

# =============================================================================
# MÓDULO 3: REGISTRO DE MOVIMIENTOS
# =============================================================================
elif menu == "💳 Movimientos Bancarios":
    st.subheader("💸 Registrar Movimiento Directo de Banco")

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
