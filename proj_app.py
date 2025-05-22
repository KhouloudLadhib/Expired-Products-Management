# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np




# Wider page for better visibility
st.set_page_config(layout="wide")



def load_default_data():
    """Load the default dataset with error handling"""
    try:
        return pd.read_csv('perishables_analysis.csv')
    except Exception as e:
        st.error(f"Failed to load default dataset: {str(e)}")
        return pd.DataFrame()  # Return empty dataframe as fallback

df = load_default_data()

# Ensure we have a valid dataframe before proceeding
if df.empty:
    st.error("No valid data available. Please check your data sources.")
    st.stop()  # Stop execution if no data




# Title and desc
st.title("📦 Expired Products Management")
st.write("Use filters to display data for your warehouse")




# Item column is string type
df['Item'] = df['Item'].astype(str)




# Filters
st.sidebar.header("Filter Options")
# Whs
st.sidebar.write("Select Warehouse:")
whs_options = df['Warehouse ID'].unique().tolist()  # Get unique warehouse IDs
whs_filter = st.sidebar.multiselect("", options=whs_options, default=whs_options,
            key="warehouse_filter", label_visibility="collapsed")   # Default is all whs
# Superclass
st.sidebar.write("Select Superclass:")
superclass_options = df['Superclass'].unique().tolist()
superclass_filter = st.sidebar.multiselect("",options=superclass_options, default=superclass_options,
    key="superclass_filter", label_visibility="collapsed")
# Months Since Received
st.sidebar.write("Months Since Received Range:")
min_months = int(df['Months since received'].min())
max_months = int(df['Months since received'].max())
months_range = st.sidebar.slider("", min_value=min_months, max_value=max_months, value=(min_months, max_months),
    key="months_range", label_visibility="collapsed")
# Expiry status
st.sidebar.write("Expiry Status:")
expired_options = df['Expired'].unique().tolist()
expired_filter = st.sidebar.multiselect("", options=expired_options, default=expired_options, key="expired_filter",
    label_visibility="collapsed")
# Expiry next month
st.sidebar.write("Expires Next Month:")
enm_options = df['Expires next month'].unique().tolist()
enm_filter = st.sidebar.multiselect("", options=enm_options, default=enm_options, key="enm_filter",
    label_visibility="collapsed")
# Filter the dataset based on all user selections
filtered_df = df[
    (df['Warehouse ID'].isin(whs_filter)) &
    (df['Superclass'].isin(superclass_filter)) &
    (df['Months since received'].between(months_range[0], months_range[1])) &
    (df['Expired'].isin(expired_filter)) &
    (df['Expires next month'].isin(enm_filter))
]



# Add column showing value for expired items
df['Expired_Value'] = df['Value'].where(df['Expired'] == 'Y', 0)
filtered_df['Expired_Value'] = filtered_df['Value'].where(filtered_df['Expired'] == 'Y', 0)
# Categorize time since received
def categorize_time(months):
    if months >= 36:
        return '> 3 years'
    elif 24 <= months < 36:
        return '2-3 years'
    elif 12 <= months < 24:
        return '1-2 years'
    else:
        return '< 1 year'
filtered_df['Time_Category'] = filtered_df['Months since received'].apply(categorize_time)



# Count items in each time category and calculate percentages for visualization later
time_counts = filtered_df['Time_Category'].value_counts().reindex(
    ['< 1 year', '1-2 years', '2-3 years', '> 3 years']).reset_index()
time_counts.columns = ['Time Since Received', 'Count']
time_counts['Percentage'] = (time_counts['Count'] / time_counts['Count'].sum()) * 100





# KPI section
st.write("## 📊 KPIs")

# Organize KPI metrics in 5 sections
col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.metric("Expired (All)", f"${df['Expired_Value'].sum():,.2f}")  # Value of all expired products at the company
with col2: st.metric("Expired (Filtered)", f"${filtered_df['Expired_Value'].sum():,.2f}")  # Expiredalue for filtered data
with col3: st.metric("Perishables Value", f"${filtered_df['Value'].sum():,.2f}")  # Total value of filtered data
# Number of items expiring next month for filtered data
with col4:
    items_expiring_next_month = filtered_df[filtered_df['Expires next month'] == 'Y']['Item'].nunique()
    st.metric("Items Expiring Next Month", items_expiring_next_month)
# Show maximum months since received in filtered data
with col5:
    max_months = filtered_df['Months since received'].max()
    st.metric("Max Months Since Received", max_months)






# Items expiring next month list
st.write("## Items Expiring Next Month")
expiring_next_month = filtered_df[filtered_df['Expires next month'] == 'Y']
if not expiring_next_month.empty:
    # Case sensitive column names (happens sometimes that the variables randomly change case in this company)
    quantity_col = next((col for col in expiring_next_month.columns if col.lower() == 'quantity on hand'), None)
    location_col = next((col for col in expiring_next_month.columns if col.lower() == 'location'), None)    
    if quantity_col and location_col:
        # Group by item, warehouse, and location
        expiring_items = expiring_next_month.groupby(['Item', 'Warehouse ID', location_col]).agg(Value=('Value', 'sum'),
            Quantity=(quantity_col, 'sum')).reset_index().sort_values('Value', ascending=False)        
        # Display dataframe
        st.dataframe(expiring_items, column_config={"Item": "Product", "Warehouse ID": "Warehouse", location_col: "Location",
                "Value": st.column_config.NumberColumn("Total Value", format="$%.2f"), "Quantity": "Quantity on Hand"},
            use_container_width=True)
    else:
        # Show warning if columns are missing (can happen if someone uploads a modified file)
        missing = []
        if not quantity_col: missing.append("Quantity on Hand")
        if not location_col: missing.append("Location")
        st.warning(f"Missing columns in data: {', '.join(missing)}")
else:
    st.success("No items expiring next month based on current filters")






# Visualization
col1, col2 = st.columns(2)
# Expired value vs total value by superclass
with col1:
    # Group by superclass
    superclass_stats = filtered_df.groupby('Superclass').agg(Total_Value=('Value', 'sum'),
        Expired_Value=('Expired_Value', 'sum')).reset_index()
    melted_df = pd.melt(superclass_stats, id_vars=['Superclass'], value_vars=['Total_Value', 'Expired_Value'],
                       var_name='Value Type', value_name='Amount')    
    # Bar graph
    fig1 = px.bar(melted_df, x='Superclass', y='Amount', color='Value Type', color_discrete_sequence=['#A8DF8E', '#3D7A4F'],
                 barmode='group', title='<b>Total Value vs Expired Value by Superclass</b>',
                 labels={'Amount': 'Value ($)', 'Superclass': 'Product Category'}, text_auto='.2s')
    # Graph layout
    fig1.update_layout(
        hovermode='x unified',  # Show hover data for all bars at same x-position
        yaxis_tickprefix='$',  # Add $
        yaxis_tickformat=',.0f',  # add ,
        xaxis={'categoryorder':'total descending'},  # Sort by value
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12, color='black'),
        legend_title_text='Value Type')
    st.plotly_chart(fig1, use_container_width=True)
# Top 10 most problematic items table (right column)
with col2:
    st.write("## Top 10 Most Problematic Items (Highest Expired Value)")    
    # Total expired value by item
    problematic_items = filtered_df[filtered_df['Expired'] == 'Y'].groupby('Item').agg(
        Total_Expired_Value=('Expired_Value', 'sum'),
    ).reset_index().sort_values('Total_Expired_Value', ascending=False).head(10)    
    # Percentage of total expired value
    total_expired = problematic_items['Total_Expired_Value'].sum()
    problematic_items['Percentage'] = (problematic_items['Total_Expired_Value'] / total_expired) * 100        
    # Format
    problematic_items['Total_Expired_Value'] = problematic_items['Total_Expired_Value'].apply(lambda x: f"${x:,.2f}")
    problematic_items['Percentage'] = problematic_items['Percentage'].apply(lambda x: f"{x:.1f}%")    
    # Show dataframe without index
    st.dataframe(
        problematic_items[['Item', 'Total_Expired_Value', 'Percentage']].set_index('Item'),
        column_config={"Total_Expired_Value": "Expired Value", "Percentage": "% of Total Expired"},
        use_container_width=True)





col1, col2 = st.columns(2)
# Expired goods value by Warehouse ID
with col1:
    wh_expired = df.groupby('Warehouse ID')['Expired_Value'].sum().reset_index()
    fig_wh = px.bar(wh_expired, x='Warehouse ID', y='Expired_Value', color='Warehouse ID',
                    title='<b>Total Expired Value by Warehouse (All Data)</b>', labels={'Expired_Value': 'Expired Value ($)'},
                    text_auto='.2s')
    fig_wh.update_layout(yaxis_tickprefix='$', yaxis_tickformat=',.0f', xaxis={'categoryorder':'total descending'},
        showlegend=False)
    st.plotly_chart(fig_wh, use_container_width=True)
# Average 12 months sales vs Expired status
with col2:
    if '12 months sales' in filtered_df.columns:
        # Average
        avg_sales_expired = filtered_df.groupby('Expired').agg( Avg_12_Month_Sales=('12 months sales', 'mean'),
            Count=('Expired', 'count')).reset_index()
        fig_sales = px.bar(avg_sales_expired, x='Expired', y='Avg_12_Month_Sales', color='Expired',
                          text='Avg_12_Month_Sales', title='<b>Average 12 Month Sales by Expiry Status</b>',
                          labels={'Avg_12_Month_Sales': 'Average Sales ($)', 'Expired': 'Expired Status'})
        fig_sales.update_traces(texttemplate='$%{y:,.0f}', textposition='outside')
        fig_sales.update_layout(yaxis_tickprefix='$', yaxis_tickformat=',.0f', showlegend=False)
        st.plotly_chart(fig_sales, use_container_width=True)
    else:
        st.warning("'12 months sales' column not found in dataset")





col1, col2 = st.columns(2)
# Time categories pie chart
with col1:
    fig_pie = px.pie(time_counts, values='Count', names='Time Since Received', title='<b>Time Since Received Distribution</b>',
                     color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#FFBE0B', '#8338EC'], hole=0.3)    
    fig_pie.update_traces(textposition='inside',
        textinfo='percent+label', insidetextfont=dict(color='white', size=14),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent:.1%}')    
    fig_pie.update_layout(
        uniformtext_minsize=12, uniformtext_mode='hide',  # Hide text if it doesn't fit
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12, color='black'),
        margin=dict(t=50, b=50, l=50, r=50))
    st.plotly_chart(fig_pie, use_container_width=True)
# Items missing shelf life
with col2:
    st.write("## ⚠️ Items With No Shelf Life Entered")
    if 'Shelf Life' in df.columns:
        no_shelf_life = df[df['Shelf Life'].isna()]['Item'].unique()
        if len(no_shelf_life) > 0:
            st.dataframe(pd.DataFrame(no_shelf_life, columns=['Items Missing Shelf Life']), use_container_width=True)
        else:
            st.success("All items have shelf life information entered")
    else:
        st.warning("No 'Shelf Life' column found in dataset")




# Full filtered dataset
st.write("### 📋 Detailed Data")
# Conditional formatting
def color_rows(row):
    if 'Shelf Life' in row.index and pd.isna(row['Shelf Life']):
        return ['background-color: #FFA500'] * len(row)  # if shelf life missing, orange
    elif row['Expired'] == 'Y':
        return ['background-color: #FF6B6B'] * len(row)  # if expired, red
    else:
        return [''] * len(row)  # if other, no color
if not filtered_df.empty:
    styled_df = filtered_df.style.apply(color_rows, axis=1)    
    # Display with column configurations
    st.dataframe(styled_df, column_config={
            "Expired": st.column_config.TextColumn("Expired", help="Y = Expired, N = Not Expired"),
            "Expires next month": st.column_config.TextColumn("Expires Next Month"),
            "Months since received": st.column_config.NumberColumn("Months Since Received"),
            "Value": st.column_config.NumberColumn("Value", format="$%.2f"),
            "Expired_Value": st.column_config.NumberColumn("Expired Value", format="$%.2f")},
        use_container_width=True,
        hide_index=True)
else:
    st.warning("No data matches the current filters")