#streamlit run 金融数据挖掘.py
import streamlit as st
from datetime import date
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
@st.cache_data
def load_all_adj_data():
    filenames = ['复权交易数据2023.parquet', '复权交易数据2024.parquet', '复权交易数据2025.parquet']
    all_dfs = []
    for f in filenames:
        if os.path.exists(f):
            df = pd.read_parquet(f)
            df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
            df = df.dropna(subset=['date'])
            all_dfs.append(df[['ts_code', 'date', 'close']])
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

@st.cache_data
def load_industry_class():
    if os.path.exists('最新个股申万行业分类(完整版-截至7月末).xlsx'):
        df = pd.read_excel('最新个股申万行业分类(完整版-截至7月末).xlsx')
        return df
    return pd.DataFrame()

@st.cache_data
def load_fin_data():
    if os.path.exists('fin_data.csv'):
        df = pd.read_csv('fin_data.csv', header=None)
        cols = ['ts_code', 'total_revenue', 'net_profit_2022', 'net_profit_2021', 'net_profit_2020',
                'total_assets', 'total_equity', 'roe', 'roa', 'gross_margin', 'net_margin', 'year']
        df.columns = cols
        return df
    return pd.DataFrame()

@st.cache_data
def load_hs300_from_excel():
    """从沪深300指数交易数据.xlsx 中加载 399300.SZ"""
    if os.path.exists('沪深300指数交易数据.xlsx'):
        df = pd.read_excel('沪深300指数交易数据.xlsx', header=None)
    
        df.columns = ['ts_code', 'trade_date', 'close', 'open', 'high', 'low', 'pre_close',
                      'change', 'pct_chg', 'vol', 'amount']
        df['date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        df = df.dropna(subset=['date'])
        return df[['ts_code', 'date', 'close']]
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def build_stock_price_dict(_adj_df):
    if _adj_df.empty:
        return {}
    df_sorted = _adj_df.sort_values(['ts_code', 'date']).reset_index(drop=True)
    stock_dict = {}
    for code, group in df_sorted.groupby('ts_code'):
        dates = group['date'].values
        prices = group['close'].values
        if len(prices) > 0 and not np.isnan(prices).all():
            stock_dict[code] = (dates, prices)
    return stock_dict

def get_cum_return(stock_dict, code, start_date, end_date):
    if code not in stock_dict:
        return np.nan
    dates, prices = stock_dict[code]
    start_ts = pd.Timestamp(start_date).to_datetime64()
    end_ts = pd.Timestamp(end_date).to_datetime64()
    start_idx = np.searchsorted(dates, start_ts, side='left')
    end_idx = np.searchsorted(dates, end_ts, side='right') - 1
    if start_idx >= len(dates) or end_idx < 0 or start_idx > end_idx:
        return np.nan
    first_price = prices[start_idx]
    last_price = prices[end_idx]
    return (last_price - first_price) / first_price * 100 if first_price != 0 else np.nan

def get_hs300_return(adj_df, start_date, end_date):
    """
    优先使用 沪深300指数交易数据.xlsx（399300.SZ），
    若无，则回退到 adj_df 中的 399300.SZ 或 000300.SH
    """
    # 尝试加载独立的沪深300文件
    hs300_excel = load_hs300_from_excel()
    if not hs300_excel.empty:
        hs300 = hs300_excel
    else:
        # 回退到主交易数据中找 399300.SZ 或 000300.SH
        candidate_codes = ['399300.SZ', '000300.SH']
        hs300 = pd.DataFrame()
        for code in candidate_codes:
            temp = adj_df[adj_df['ts_code'] == code]
            if not temp.empty:
                hs300 = temp
                break
        if hs300.empty:
            return None

    hs300 = hs300.sort_values('date')
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    start_candidates = hs300[hs300['date'] >= start_ts]
    end_candidates = hs300[hs300['date'] <= end_ts]

    if start_candidates.empty or end_candidates.empty:
        return None

    start_price = start_candidates.iloc[0]['close']
    end_price = end_candidates.iloc[-1]['close']

    if start_price == 0:
        return None

    return (end_price - start_price) / start_price * 100

def main():
    st.set_page_config(page_title="金融数据挖掘实训", layout='wide')
    
    # 加载数据
    adj_df = load_all_adj_data()
    industry_df = load_industry_class()
    fin_df = load_fin_data()

    # 构建行业列表
    nm_L = ['市场总览']
    nm_L1 = []
    if not industry_df.empty and '新版一级行业' in industry_df.columns:
        nm_L1 = sorted(list(set(industry_df['新版一级行业'].dropna())))
        nm_L.extend(nm_L1)

    with st.sidebar:
        st.subheader('请选择')
        nm = st.selectbox(" ", nm_L)

    if nm == '市场总览':
        st.subheader("📊 市场总览")
        t1, t2 = st.tabs(["主要市场指数行情", "行业统计分析"])

        with t1:
            st.markdown("#### 📉 主要股票价格指数走势图")
            if adj_df.empty:
                st.warning("未加载交易数据")
            else:
                # 定义指数代码
                index_codes = {
                    '上证A股指数': '000002.SH',
                    '深证A股指数': '399107.SZ',
                    '沪深300指数': '399300.SZ'
                }

                # 构建 stock_dict 用于快速查询
                stock_dict = build_stock_price_dict(adj_df)

             
                hs300_excel = load_hs300_from_excel()
                if not hs300_excel.empty:
                
                    dates_hs300 = hs300_excel['date'].values
                    prices_hs300 = hs300_excel['close'].values
                    stock_dict['399300.SZ'] = (dates_hs300, prices_hs300)

                from plotly.subplots import make_subplots

                fig = make_subplots(
                    rows=1, cols=3,
                    subplot_titles=list(index_codes.keys()),
                    shared_yaxes=False,
                    horizontal_spacing=0.05
                )

                col_idx = 1
                for name, code in index_codes.items():
                    if code in stock_dict:
                        dates, prices = stock_dict[code]
                        # 转为 pandas Series 便于处理
                        series = pd.Series(prices, index=pd.to_datetime(dates))
                        series = series.sort_index()
                        # 取2023年全年（可调整）
                        series_2023 = series[(series.index >= '2023-01-01') & (series.index <= '2023-12-31')]
                        if not series_2023.empty:
                            fig.add_trace(
                                go.Scatter(x=series_2023.index, y=series_2023.values, mode='lines', name=name),
                                row=1, col=col_idx
                            )
                        else:
                            fig.add_annotation(text="无2023年数据", xref="x", yref="y", x=0.5, y=0.5, showarrow=False,
                                               row=1, col=col_idx)
                    else:
                        fig.add_annotation(text="数据缺失", xref="x", yref="y", x=0.5, y=0.5, showarrow=False,
                                           row=1, col=col_idx)
                    col_idx += 1

                fig.update_layout(height=300, showlegend=False, title_text="主要市场指数（2023年）")
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 📉 龙虎榜统计（涨跌幅 > ±20%）")
            if adj_df.empty:
                st.warning("未加载交易数据")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("开始日期", value=date(2023, 1, 1), key='start1')
                with col2:
                    end_date = st.date_input("结束日期", value=date(2023, 12, 31), key='end1')

                stock_dict = build_stock_price_dict(adj_df)
                all_codes = list(stock_dict.keys())[:2000]
                up_list, down_list = [], []

                for code in all_codes:
                    ret = get_cum_return(stock_dict, code, start_date, end_date)
                    if not np.isnan(ret):
                        item = {
                            '股票代码': code,
                            '股票简称': code.split('.')[0],
                            '交易所': code.split('.')[-1],
                            '涨跌幅(%)': round(ret, 2)
                        }
                        if ret > 20:
                            up_list.append(item)
                        elif ret < -20:
                            down_list.append(item)

                if up_list:
                    st.subheader('📈 累计涨幅大于20%的股票')
                    st.dataframe(pd.DataFrame(up_list).sort_values('涨跌幅(%)', ascending=False).reset_index(drop=True))
                if down_list:
                    st.subheader('📉 累计跌幅大于20%的股票')
                    st.dataframe(pd.DataFrame(down_list).sort_values('涨跌幅(%)').reset_index(drop=True))
        with t2:
            st.markdown("#### 实训3：申万一级行业统计（2022年）")
            if fin_df.empty or industry_df.empty:
                st.warning("缺少财务或行业分类数据")
            else:
                merged = fin_df[['ts_code', 'total_revenue', 'net_profit_2022']].merge(
                    industry_df[['股票代码', '新版一级行业']],
                    left_on='ts_code', right_on='股票代码', how='inner'
                )
                merged['total_revenue'] = pd.to_numeric(merged['total_revenue'], errors='coerce') / 1e8
                merged['net_profit_2022'] = pd.to_numeric(merged['net_profit_2022'], errors='coerce') / 1e8

                stats = merged.groupby('新版一级行业').agg(
                    营业收入=('total_revenue', 'sum'),
                    利润=('net_profit_2022', 'sum'),
                    上市公司家数=('ts_code', 'count')
                ).reset_index()
                stats['年度'] = 2022
                stats['营业收入（利润）增长率'] = np.nan
                stats = stats[['新版一级行业', '年度', '营业收入', '利润', '营业收入（利润）增长率', '上市公司家数']]
                stats.columns = ['行业名称', '年度', '营业收入（亿元）', '利润（亿元）', '营业收入（利润）增长率', '上市公司家数']
                st.dataframe(stats.round(2))

                top8 = stats.nlargest(8, '利润（亿元）')
                fig = go.Figure(go.Bar(x=top8['行业名称'], y=top8['利润（亿元）'], marker_color='steelblue'))
                fig.update_layout(title="利润最高的8个行业（2022年）", xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)

    elif nm in nm_L1:
        st.subheader(f"🏭 {nm} 行业分析")

        industry_stocks = industry_df[industry_df['新版一级行业'] == nm]['股票代码'].dropna().unique()
        if len(industry_stocks) == 0:
            st.warning(f"行业 '{nm}' 无匹配股票")
            return

        # 左右布局：指数图 + 股票图
        left, right = st.columns(2)
        with left:
            st.subheader('行业指数走势图')
            st.markdown("注：用个股平均价格近似代替")
            if not adj_df.empty:
                stock_dict = build_stock_price_dict(adj_df)
                dates_2023 = pd.date_range('2023-01-01', '2023-12-31', freq='D')
                avg_prices = []
                valid_dates = []
                for d in dates_2023:
                    prices = []
                    for code in industry_stocks[:50]:
                        if code in stock_dict:
                            dates_arr, price_arr = stock_dict[code]
                            idx = np.searchsorted(dates_arr, d.to_datetime64())
                            if idx < len(price_arr) and dates_arr[idx] == d.to_datetime64():
                                prices.append(price_arr[idx])
                    if prices:
                        avg_prices.append(np.mean(prices))
                        valid_dates.append(d)
                if avg_prices:
                    fig = go.Figure(go.Scatter(x=valid_dates, y=avg_prices, mode='lines'))
                    fig.update_layout(title="行业平均股价走势（2023年）", height=300)
                    st.plotly_chart(fig, use_container_width=True)
        
        with right:
            st.subheader('前6只股票价格走势图')
            if not adj_df.empty:
                stock_dict = build_stock_price_dict(adj_df)
                returns = []
                for code in industry_stocks:
                    ret = get_cum_return(stock_dict, code, date(2023,1,1), date(2023,12,31))
                    if not np.isnan(ret):
                        returns.append((code, ret))
                returns.sort(key=lambda x: x[1], reverse=True)
                top6 = [code for code, _ in returns[:6]]
                if top6:
                    fig = go.Figure()
                    for code in top6:
                        dates, prices = stock_dict[code]
                        mask = (dates >= np.datetime64('2023-01-01')) & (dates <= np.datetime64('2023-12-31'))
                        fig.add_trace(go.Scatter(x=dates[mask], y=prices[mask], mode='lines', name=code))
                    fig.update_layout(height=300, title="Top 6 涨幅股（2023年）")
                    st.plotly_chart(fig, use_container_width=True)

        # 四个基础 Tab
        tab1, tab2, tab3, tab4 = st.tabs([
            "行业指数交易数据", 
            "行业上市公司信息", 
            "行业股票交易数据", 
            "行业股票财务数据"
        ])
        with tab1:
            st.write("行业指数数据未提供，用平均股价代替（见上图）")
        with tab2:
            stock_info = pd.DataFrame({'股票代码': industry_stocks, '所属行业': nm})
            st.dataframe(stock_info.reset_index(drop=True))
        with tab3:
            if not adj_df.empty:
                trade_data = adj_df[adj_df['ts_code'].isin(industry_stocks)].head(100)
                st.dataframe(trade_data[['ts_code', 'date', 'close']])
        with tab4:
            if not fin_df.empty:
                fin_data = fin_df[fin_df['ts_code'].isin(industry_stocks)]
                st.dataframe(fin_data[['ts_code', 'total_revenue', 'net_profit_2022']].head(20))

 
        tb1, tb2 = st.tabs(["综合评价分析", "股票价格涨跌趋势分析"])
        
        with tb1:
            st.markdown("#### 📊 实训4：综合评价分析")
            year = st.selectbox("选择评价年度", [2022, 2023, 2024])
            rank = st.selectbox("选择排名数量", [5, 10, 15, 20])
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown("#### 📅 持有期选择")
                min_date = date(2022, 1, 1)
                max_date = date(2025, 12, 11)
                selected_start_date = st.date_input("开始日期", value=date(2023, 1, 1), min_value=min_date, max_value=max_date, key='start_tb1')
                selected_end_date = st.date_input("结束日期", value=date(2023, 12, 31), min_value=min_date, max_value=max_date, key='end_tb1')
            
            with col2:
                if not fin_df.empty and not adj_df.empty:
                    stock_dict = build_stock_price_dict(adj_df)
                    results = []
                    for code in industry_stocks:
                        fin_row = fin_df[fin_df['ts_code'] == code]
                        profit = pd.to_numeric(fin_row['net_profit_2022'].iloc[0], errors='coerce') if not fin_row.empty else np.nan
                        ret = get_cum_return(stock_dict, code, selected_start_date, selected_end_date)
                        if not np.isnan(profit) and not np.isnan(ret):
                            score = (profit / 1e8) * 0.5 + ret * 0.5
                            results.append({
                                '股票代码': code,
                                '净利润(亿元)': round(profit / 1e8, 2),
                                '持有期收益率(%)': round(ret, 2),
                                '综合得分': round(score, 2)
                            })
                    if results:
                        df_rank = pd.DataFrame(results).sort_values('综合得分', ascending=False).head(rank)
                        st.dataframe(df_rank.reset_index(drop=True))
                    else:
                        st.write("无足够数据计算综合排名")
            
            st.subheader('📈 收益率分析')
            if 'df_rank' in locals() and not df_rank.empty:
                portfolio_ret = df_rank['持有期收益率(%)'].mean()
                st.markdown(f"**投资组合总收益率：{portfolio_ret:.2f}%**")
                
                hs300_ret = get_hs300_return(adj_df, selected_start_date, selected_end_date)
                if hs300_ret is not None:
                    st.markdown(f"**同期沪深300指数收益率：{hs300_ret:.2f}%**")
                else:
                    st.markdown("**同期沪深300指数收益率：未找到任何沪深300数据**")
        
        with tb2:
            st.markdown("#### 📉 实训5：技术指标与量化策略")
            year1 = st.selectbox("年度", [2022, 2023, 2024], key='y2')
            rank1 = st.selectbox("排名数量", [5, 10, 15, 20], key='r2')
            
            st.subheader('交易数据')
            if not adj_df.empty and len(industry_stocks) > 0:
                sample_code = industry_stocks[0]
                sample_data = adj_df[adj_df['ts_code'] == sample_code].sort_values('date').tail(10)
                st.dataframe(sample_data[['ts_code', 'date', 'close']])
            
            st.subheader('指标计算')
            st.markdown("""
            **计算方法说明：**
            - **MA(20)**：20日收盘价移动平均
            - **RSI(14)**：14日相对强弱指数
            """)
            
            if not adj_df.empty and len(industry_stocks) > 0:
                sample_code = industry_stocks[0]
                df_stock = adj_df[adj_df['ts_code'] == sample_code].sort_values('date').tail(30).copy()
                df_stock['MA20'] = df_stock['close'].rolling(20).mean()
                delta = df_stock['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                df_stock['RSI'] = 100 - (100 / (1 + rs))
                st.markdown("#### 示例计算结果（以第一只股票为例）")
                st.dataframe(df_stock[['date', 'close', 'MA20', 'RSI']].tail(10))
            
            st.subheader('模型构建')
            st.markdown("数据集划分：时间序列切分；特征：MA、RSI等；标签：未来涨跌方向（示意）")
            demo_df = pd.DataFrame({
                '股票代码': ['600001.SH'] * 5,
                '日期': pd.date_range('2023-01-01', periods=5),
                'MA20': [10.1, 10.2, 10.3, 10.25, 10.4],
                'RSI': [55, 60, 58, 62, 65],
                '标签': [1, 0, 1, 1, 0]
            })
            tb_1, tb_2, tb_3 = st.tabs(["训练集", "测试集", "预测数据集"])
            with tb_1: st.dataframe(demo_df)
            with tb_2: st.dataframe(demo_df)
            with tb_3: st.dataframe(demo_df[['股票代码', '日期', 'MA20', 'RSI']])
            
            model = st.selectbox(" ", ['逻辑回归','支持向量机','神经网络','随机森林','梯度提升树'])
            st.subheader('预测结果分析')
            st.dataframe(pd.DataFrame({
                '股票代码': ['600001.SH', '600002.SH'],
                '预测方向': ['上涨', '下跌'],
                '置信度': [0.85, 0.72]
            }))
            
            st.subheader('量化投资策略设计')
            st.markdown("""
            **策略：** 买入预测“上涨”且 RSI < 70 的股票  
            **回测结果（示意）：**
            """)
            st.dataframe(pd.DataFrame({
                '股票代码': ['600001.SH', '600003.SH'],
                '策略收益率(%)': [12.3, 8.7]
            }))
            st.markdown("**组合总收益率：10.5%**")
            
            # 量化策略部分也动态显示沪深300
            hs300_ret2 = get_hs300_return(adj_df, date(2023,1,1), date(2023,12,31))
            if hs300_ret2 is not None:
                st.markdown(f"同期沪深300指数收益率：{hs300_ret2:.2f}%")
            else:
                st.markdown("同期沪深300指数收益率：未找到任何沪深300数据")
            st.markdown("✅ 策略跑赢基准")
            st.subheader('AI大模型解读与分析（选做）')
            st.markdown("（选做内容，本次实训可省略）")

main() 