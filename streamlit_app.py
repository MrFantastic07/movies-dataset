import streamlit as st
import pandas as pd
from io import StringIO
import json
import math

# Title
st.title('Cut Plan Calculator')

# Product Input
st.subheader('Product Input')
products = []
product_data = []

if 'products' not in st.session_state:
    st.session_state['products'] = []

if 'cut_plans' not in st.session_state:
    st.session_state['cut_plans'] = []

# Add product function
def add_product():
    product = {
        'name': st.session_state.name,
        'bite': st.session_state.bite,
        'perimeter': st.session_state.perimeter,
        'panels': st.session_state.panels,
        'fabricType': st.session_state.fabricType,
        'color': st.session_state.color,
        'quantity': st.session_state.quantity
    }
    st.session_state['products'].append(product)

# Product form
with st.form(key='product_form'):
    st.text_input('Name', key='name')
    st.number_input('Bite (yards)', key='bite', step=0.01, min_value=0.0)
    st.number_input('Perimeter (yards)', key='perimeter', step=0.01, min_value=0.0)
    st.number_input('Panels', key='panels', min_value=1)
    st.text_input('Fabric Type', key='fabricType')
    st.text_input('Color', key='color')
    st.number_input('Quantity', key='quantity', min_value=1)
    submit_button = st.form_submit_button(label='Add Product', on_click=add_product)

# Display added products
if st.session_state['products']:
    st.write(pd.DataFrame(st.session_state['products']))

# Common Inputs
st.subheader('Common Inputs')
table_length = st.number_input('Table Length (yards)', step=0.01, min_value=0.0)
max_ply = st.number_input('Max Ply', min_value=1)

# Optional Inputs
st.subheader('Optional Inputs')
allow_overproduction = st.checkbox('Allow Overproduction')
optimization_priority = st.selectbox('Optimization Priority', ['ply', 'length'])
use_parity_grouping = st.checkbox('Use Parity Grouping')

# Helper functions
def group_products(products):
    groups = {}
    for product in products:
        color = product['color'] or 'Unspecified'
        key = color
        if use_parity_grouping:
            parity = 'even' if product['quantity'] % 2 == 0 else 'odd'
            key += f'-{parity}'
        if key not in groups:
            groups[key] = []
        groups[key].append(product)
    return groups

def calculate_spread(products, table_length, max_ply):
    spread = {'plies': 0, 'length': 0, 'products': []}
    remaining_length = table_length
    products = sorted(products, key=lambda x: -x['bite'])
    for product in products:
        max_units = math.floor(remaining_length / product['bite'])
        units_per_ply = min(max_units, math.ceil(product['quantity'] / max_ply))
        if use_parity_grouping and product['quantity'] % 2 != units_per_ply % 2:
            units_per_ply = max(1, units_per_ply - 1)
        if units_per_ply > 0:
            product_length = units_per_ply * product['bite']
            spread['length'] = max(spread['length'], product_length)
            remaining_length -= product_length
            plies_needed = math.ceil(product['quantity'] / units_per_ply)
            spread['plies'] = max(spread['plies'], plies_needed)
            spread['products'].append({
                'name': product['name'],
                'unitsPerPly': units_per_ply,
                'totalUnits': units_per_ply * spread['plies'],
                'requiredUnits': product['quantity']
            })
    return spread

def update_remaining_products(products, spread):
    remaining_products = []
    for product in products:
        produced_product = next((p for p in spread['products'] if p['name'] == product['name']), None)
        if produced_product:
            product['quantity'] -= produced_product['totalUnits']
        if product['quantity'] > 0:
            remaining_products.append(product)
    return remaining_products

def calculate_cut_plans(products, table_length, max_ply):
    cut_plans = []
    products_to_process = group_products(products)
    for group_key, products in products_to_process.items():
        color, parity = group_key.split('-') if '-' in group_key else (group_key, 'N/A')
        group_plan = {'color': color, 'parity': parity, 'spreads': []}
        remaining_products = products.copy()
        while remaining_products:
            spread = calculate_spread(remaining_products, table_length, max_ply)
            group_plan['spreads'].append(spread)
            remaining_products = update_remaining_products(remaining_products, spread)
        cut_plans.append(group_plan)
    return cut_plans

# Calculate Cut Plans button
if st.button('Calculate Cut Plans'):
    cut_plans = calculate_cut_plans(st.session_state['products'], table_length, max_ply)
    st.session_state['cut_plans'] = cut_plans

# Display Cut Plans
if st.session_state['cut_plans']:
    st.subheader('Cut Plans')
    for index, plan in enumerate(st.session_state['cut_plans']):
        st.write(f"Cut Plan {index + 1}: Color: {plan['color']}, Parity: {plan['parity']}")
        for spread_index, spread in enumerate(plan['spreads']):
            st.write(f"Spread {spread_index + 1}: Plies: {spread['plies']}, Length: {spread['length']:.2f} yards")
            for product in spread['products']:
                st.write(f"{product['name']}: {product['unitsPerPly']} units/ply ({product['totalUnits']} total)")

# Summary Statistics
if st.session_state['cut_plans']:
    total_spreads = sum(len(plan['spreads']) for plan in st.session_state['cut_plans'])
    total_fabric_used = sum(spread['length'] for plan in st.session_state['cut_plans'] for spread in plan['spreads'])
    total_plies = sum(spread['plies'] for plan in st.session_state['cut_plans'] for spread in plan['spreads'])
    average_ply_count = total_plies / total_spreads if total_spreads > 0 else 0
    total_overproduction = sum(
        max(0, product['totalUnits'] - product['requiredUnits'])
        for plan in st.session_state['cut_plans']
        for spread in plan['spreads']
        for product in spread['products']
    )

    st.subheader('Summary Statistics')
    st.write(f"Total number of spreads: {total_spreads}")
    st.write(f"Total fabric used: {total_fabric_used:.2f} yards")
    st.write(f"Average ply count: {average_ply_count:.2f}")
    st.write(f"Total overproduction: {total_overproduction} units")

# Export to CSV function
def export_to_csv():
    csv_data = StringIO()
    csv_data.write("Cut Plan Report\n\n")

    # Input summary
    csv_data.write("Input Summary\n")
    csv_data.write(f"Table Length,{table_length}\n")
    csv_data.write(f"Max Ply,{max_ply}\n")
    csv_data.write(f"Optimization Priority,{optimization_priority}\n")
    csv_data.write(f"Parity Grouping,{use_parity_grouping}\n\n")

    # Cut plans
    for index, plan in enumerate(st.session_state['cut_plans']):
        csv_data.write(f"Cut Plan {index + 1},{plan['color']},{plan['parity']}\n")
        for spread_index, spread in enumerate(plan['spreads']):
            csv_data.write(f"Spread {spread_index + 1},Plies,{spread['plies']},Length,{spread['length']:.2f}\n")
            csv_data.write("Product,Units/Ply,Total Units\n")
            for product in spread['products']:
                csv_data.write(f"{product['name']},{product['unitsPerPly']},{product['totalUnits']}\n")
            csv_data.write("\n")

    # Summary statistics
    csv_data.write("Summary Statistics\n")
    csv_data.write(f"Total Spreads,{total_spreads}\n")
    csv_data.write(f"Total Fabric Used,{total_fabric_used:.2f}\n")
    csv_data.write(f"Average Ply Count,{average_ply_count:.2f}\n")
    csv_data.write(f"Total Overproduction,{total_overproduction}\n")

    st.download_button(
        label="Export to CSV",
        data=csv_data.getvalue(),
        file_name="cut_plan_report.csv",
        mime="text/csv"
    )

# Export to CSV button
if st.session_state['cut_plans']:
    export_to_csv()
