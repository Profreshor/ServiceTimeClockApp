# utils/transform_utils.py
"""
Transformation utilities for the Warner Service Time Clock app.
Translates Power BI / DAX logic into Python + Pandas equivalents.
"""

import pandas as pd
from datetime import datetime, timedelta

# -------------------------------------------------------------
# Context builders (mimic CALCULATE/FILTER)
# -------------------------------------------------------------
def build_contexts(df: pd.DataFrame):
    """Split the raw punch data into contextual DataFrames."""
    att  = df[df['ItmTypDes'].str.lower().eq('attendance')].copy()
    shop = df[df['ItmTypDes'].str.lower().eq('shop-floor')].copy()
    open_att  = att[att['DateEnd'].isna()].copy()
    open_shop = shop[shop['DateEnd'].isna()].copy()
    return att, shop, open_att, open_shop


# -------------------------------------------------------------
# Technician-level summary (translates main DAX measures)
# -------------------------------------------------------------
def summarize_technicians(df: pd.DataFrame, branch_id: int | None = None) -> pd.DataFrame:
    """
    Produces a per-technician summary mimicking Power BI roster metrics:
    Clock Status, On Work Order, Current RO, Job, Customer, Start Time, Elapsed Time, Hours, Idle Time (current + total)
    """
    if branch_id is not None:
        df = df[df['BrnId'] == branch_id]

    att, shop, open_att, open_shop = build_contexts(df)
    now = datetime.utcnow() - timedelta(hours=6)  # Saskatchewan local time

    summaries = []
    for emp_id, tech in df.groupby('EmpId'):
        rec = {
            'EmpId': emp_id,
            'EmpName': tech['EmpName'].iloc[0],
            'BrnId': tech['BrnId'].iloc[0]
        }

        # Clock Status
        rec['ClockStatus'] = 'Clocked-In' if not open_att[open_att['EmpId'].eq(emp_id)].empty else 'Off Clock'

        # On Work Order
        open_ro = open_shop[open_shop['EmpId'].eq(emp_id)]
        rec['OnWorkOrder'] = 'On RO' if not open_ro.empty else 'Not on RO'

        # Current RO / Job / Customer / Start / Elapsed
        if not open_ro.empty:
            row = open_ro.iloc[-1]
            rec['CurrentRO'] = row.get('SlsId')
            rec['Job'] = row.get('OpsId')  # new field
            rec['CurrentCustomer'] = str(row.get('CusName'))[:20] if pd.notna(row.get('CusName')) else None
            ro_start = row.get('DateStart')
            rec['ROStartTime'] = ro_start.strftime('%H:%M') if pd.notna(ro_start) else None
            delta = now - ro_start
            rec['TimeElapsed'] = f"{int(delta.seconds//3600):02}:{int((delta.seconds%3600)//60):02}"
        else:
            rec.update({'CurrentRO': None, 'Job': None, 'CurrentCustomer': None, 'ROStartTime': None, 'TimeElapsed': None})

        # Hours (open Shop-Floor only)
        filt = (shop['EmpId'] == emp_id) & (shop['DateEnd'].isna())
        rec['HrsActual'] = round(shop.loc[filt, 'HrsActual'].sum(), 2)
        rec['HrsBill']   = round(shop.loc[filt, 'HrsBill'].sum(), 2)

        # -------------------------------------------------------------
        # Current Idle Time (Roster)
        # -------------------------------------------------------------
        shift_start = (
            att[
                (att['EmpId'] == emp_id)
                & (att['ItmTypDes'].str.lower() == 'attendance')
                & (att['DateEnd'].isna())
            ]["DateStart"].max()
        )

        on_shop_floor = not open_ro.empty
        last_ro_end = (
            shop[
                (shop['EmpId'] == emp_id)
                & (shop['ItmTypDes'].str.lower() == 'shop-floor')
                & (shop['DateEnd'].notna())
                & (shop['DateEnd'].dt.date == now.date())
            ]["DateEnd"].max()
        )

        idle_since = last_ro_end if pd.notna(last_ro_end) else shift_start

        if pd.notna(shift_start) and not on_shop_floor and pd.notna(idle_since):
            delta = now - idle_since
            rec['CurrentIdle'] = f"{int(delta.seconds//3600):02}:{int((delta.seconds%3600)//60):02}"
        else:
            rec['CurrentIdle'] = None

        # -------------------------------------------------------------
        # Total Idle Time (Accumulated Today)
        # -------------------------------------------------------------
        # Shift start = first attendance punch today
        shift_start_today = (
            att[
                (att['EmpId'] == emp_id)
                & (att['DateStart'].dt.date == now.date())
            ]["DateStart"].min()
        )

        if pd.notna(shift_start_today):
            # All Shop-Floor punches for today
            shop_today = shop[
                (shop['EmpId'] == emp_id)
                & (shop['DateStart'].dt.date == now.date())
            ].copy()

            total_ro_seconds = 0
            for _, row in shop_today.iterrows():
                start = row['DateStart']
                end = row['DateEnd'] if pd.notna(row['DateEnd']) else now
                total_ro_seconds += (end - start).total_seconds()

            total_shift_seconds = (now - shift_start_today).total_seconds()
            idle_seconds = max(total_shift_seconds - total_ro_seconds, 0)
            idle_hours = int(idle_seconds // 3600)
            idle_minutes = int((idle_seconds % 3600) // 60)
            rec['TotalIdle'] = f"{idle_hours:02}:{idle_minutes:02}"
        else:
            rec['TotalIdle'] = None

        summaries.append(rec)

    return pd.DataFrame(summaries)


# -------------------------------------------------------------
# Local test (optional)
# -------------------------------------------------------------
if __name__ == "__main__":
    from utils.db_utils import fetch_punches_today
    df = fetch_punches_today()
    summary = summarize_technicians(df)
    print(summary.head())