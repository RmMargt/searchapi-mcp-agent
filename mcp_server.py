# 建议将此代码保存为 mcp_server.py

import os
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta

# 添加 dotenv 支持
from dotenv import load_dotenv
load_dotenv() # 启动时加载 .env 文件

# 从环境变量中读取 API Key，更安全
SEARCHAPI_API_KEY = os.environ.get("SEARCHAPI_API_KEY") # 重要：运行前请设置环境变量 SEARCHAPI_API_KEY

if not SEARCHAPI_API_KEY:
    print("错误：请设置环境变量 SEARCHAPI_API_KEY 或创建 .env 文件并包含该变量")
    # exit(1) # 如果希望在API Key缺失时阻止服务器启动，可以取消此注释

# 初始化 FastMCP 服务器
mcp = FastMCP("searchapi")

# 常量
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"

async def make_searchapi_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """向searchapi.io发送请求并处理错误情况"""
    # 确保API Key被添加到参数中
    params["api_key"] = SEARCHAPI_API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SEARCHAPI_URL, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            error_detail = None
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.json()
            except ValueError:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.text
            
            error_message = f"调用searchapi.io时出错: {e}"
            if error_detail:
                error_message += f", 详情: {error_detail}"
            
            return {"error": error_message}
        except Exception as e:
            return {"error": f"处理请求时发生未知错误: {e}"}

@mcp.tool()
async def search_google_maps(query: str, location_ll: str = None) -> Dict[str, Any]:
    """搜索Google地图上的地点或服务"""
    params = {
        "engine": "google_maps",
        "q": query
    }
    
    if location_ll:
        params["ll"] = location_ll
    
    return await make_searchapi_request(params)

@mcp.tool()
async def search_google_flights(
    departure_id: str, 
    arrival_id: str, 
    outbound_date: str, 
    flight_type: str = "round_trip", 
    return_date: str = None,
    gl: str = None,
    hl: str = None,
    currency: str = None,
    travel_class: str = None,
    stops: str = None,
    sort_by: str = None,
    adults: str = None,
    children: str = None,
    multi_city_json: str = None,
    show_cheapest_flights: str = None,
    show_hidden_flights: str = None,
    max_price: str = None,
    carry_on_bags: str = None,
    checked_bags: str = None,
    included_airlines: str = None,
    excluded_airlines: str = None,
    outbound_times: str = None,
    return_times: str = None,
    emissions: str = None,
    included_connecting_airports: str = None,
    excluded_connecting_airports: str = None,
    layover_duration_min: str = None,
    layover_duration_max: str = None,
    max_flight_duration: str = None,
    separate_tickets: str = None,
    infants_in_seat: str = None,
    infants_on_lap: str = None,
    departure_token: str = None,
    booking_token: str = None
) -> Dict[str, Any]:
    """搜索Google航班信息"""
    params = {
        "engine": "google_flights",
        "flight_type": flight_type
    }
    
    # 处理flight_type不同情况下的必填参数
    if flight_type == "multi_city":
        if not multi_city_json:
            return {"error": "多城市行程需要'multi_city_json'参数"}
        params["multi_city_json"] = multi_city_json
    else:
        params["departure_id"] = departure_id
        params["arrival_id"] = arrival_id
        params["outbound_date"] = outbound_date
        
        if flight_type == "round_trip":
            if not return_date:
                return {"error": "往返行程需要'return_date'参数"}
            params["return_date"] = return_date
    
    # 添加可选参数
    optional_params = {
        "gl": gl,
        "hl": hl,
        "currency": currency,
        "travel_class": travel_class,
        "stops": stops,
        "sort_by": sort_by,
        "adults": adults,
        "children": children,
        "show_cheapest_flights": show_cheapest_flights,
        "show_hidden_flights": show_hidden_flights,
        "max_price": max_price,
        "carry_on_bags": carry_on_bags,
        "checked_bags": checked_bags,
        "included_airlines": included_airlines,
        "excluded_airlines": excluded_airlines,
        "outbound_times": outbound_times,
        "return_times": return_times,
        "emissions": emissions,
        "included_connecting_airports": included_connecting_airports,
        "excluded_connecting_airports": excluded_connecting_airports,
        "layover_duration_min": layover_duration_min,
        "layover_duration_max": layover_duration_max,
        "max_flight_duration": max_flight_duration,
        "separate_tickets": separate_tickets,
        "infants_in_seat": infants_in_seat,
        "infants_on_lap": infants_on_lap,
        "departure_token": departure_token,
        "booking_token": booking_token
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

@mcp.tool()
async def search_google_hotels(
    q: str, 
    check_in_date: str, 
    check_out_date: str,
    gl: str = None,
    hl: str = None,
    currency: str = None,
    property_type: str = None,
    sort_by: str = None,
    price_min: str = None,
    price_max: str = None,
    property_types: str = None,
    amenities: str = None,
    rating: str = None,
    free_cancellation: str = None,
    special_offers: str = None,
    for_displaced_individuals: str = None,
    eco_certified: str = None,
    hotel_class: str = None,
    brands: str = None,
    bedrooms: str = None,
    bathrooms: str = None,
    adults: str = None,
    children_ages: str = None,
    next_page_token: str = None
) -> Dict[str, Any]:
    """搜索Google酒店信息"""
    params = {
        "engine": "google_hotels",
        "q": q,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date
    }
    
    # 添加可选参数
    optional_params = {
        "gl": gl,
        "hl": hl,
        "currency": currency,
        "property_type": property_type,
        "sort_by": sort_by,
        "price_min": price_min,
        "price_max": price_max,
        "property_types": property_types,
        "amenities": amenities,
        "rating": rating,
        "free_cancellation": free_cancellation,
        "special_offers": special_offers,
        "for_displaced_individuals": for_displaced_individuals,
        "eco_certified": eco_certified,
        "hotel_class": hotel_class,
        "brands": brands,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "adults": adults,
        "children_ages": children_ages,
        "next_page_token": next_page_token,
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

@mcp.tool()
async def search_google_maps_reviews(
    place_id: str = None,
    data_id: str = None,
    topic_id: str = None,
    next_page_token: str = None,
    sort_by: str = None,
    rating: str = None,
    hl: str = None,
    gl: str = None,
    reviews_limit: str = None
) -> Dict[str, Any]:
    """查找地点的Google地图评论"""
    params = {
        "engine": "google_maps_reviews",
    }
    
    # 检查必填参数
    if place_id:
        params["place_id"] = place_id
    elif data_id:
        params["data_id"] = data_id
    else:
        return {"error": "需要提供'place_id'或'data_id'参数"}
    
    # 添加可选参数
    optional_params = {
        "topic_id": topic_id,
        "next_page_token": next_page_token,
        "sort_by": sort_by,
        "rating": rating,
        "hl": hl,
        "gl": gl,
        "reviews_limit": reviews_limit
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

@mcp.tool()
async def search_google_hotels_property(
    property_token: str,
    check_in_date: str,
    check_out_date: str,
    gl: str = None,
    hl: str = None,
    currency: str = None,
    adults: str = None,
    children: str = None,
    children_ages: str = None
) -> Dict[str, Any]:
    """获取Google酒店详细信息"""
    params = {
        "engine": "google_hotels_property",
        "property_token": property_token,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date
    }
    
    # 添加可选参数
    optional_params = {
        "gl": gl,
        "hl": hl,
        "currency": currency,
        "adults": adults,
        "children": children,
        "children_ages": children_ages
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

@mcp.tool()
async def search_google_flights_calendar(
    flight_type: str,
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str = None,
    outbound_date_start: str = None,
    outbound_date_end: str = None,
    return_date_start: str = None,
    return_date_end: str = None,
    gl: str = None,
    hl: str = None,
    currency: str = None,
    adults: str = None,
    children: str = None,
    travel_class: str = None,
    stops: str = None
) -> Dict[str, Any]:
    """搜索Google航班价格日历"""
    params = {
        "engine": "google_flights_calendar",
        "flight_type": flight_type,
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date
    }
    
    # 往返航班需要return_date
    if flight_type == "round_trip":
        if not return_date:
            return {"error": "往返航班需要'return_date'参数"}
        params["return_date"] = return_date
    
    # 添加日期范围参数
    if outbound_date_start:
        params["outbound_date_start"] = outbound_date_start
    
    if outbound_date_end:
        params["outbound_date_end"] = outbound_date_end
    
    if return_date_start and flight_type == "round_trip":
        params["return_date_start"] = return_date_start
    
    if return_date_end and flight_type == "round_trip":
        params["return_date_end"] = return_date_end
    
    # 添加可选参数
    optional_params = {
        "gl": gl,
        "hl": hl,
        "currency": currency,
        "adults": adults,
        "children": children,
        "travel_class": travel_class,
        "stops": stops
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

@mcp.tool()
async def get_current_time(
    format: str = "iso", 
    days_offset: str = "0",
    return_future_dates: str = "false",
    future_days: str = "7"
) -> Dict[str, Any]:
    """获取当前时间，支持不同格式和日期偏移"""
    try:
        # 转换偏移天数
        offset = int(days_offset)
        
        # 获取当前日期时间
        current_dt = datetime.now()
        
        # 应用偏移
        if offset != 0:
            current_dt += timedelta(days=offset)
        
        # 格式化结果
        result = {}
        
        # 基本格式
        if format == "iso":
            result["datetime"] = current_dt.isoformat()
        elif format == "slash":
            result["date"] = current_dt.strftime("%Y/%m/%d")
            result["time"] = current_dt.strftime("%H:%M:%S")
        elif format == "chinese":
            result["date"] = current_dt.strftime("%Y年%m月%d日")
            result["time"] = current_dt.strftime("%H时%M分%S秒")
            result["weekday"] = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][current_dt.weekday()]
        elif format == "timestamp":
            result["timestamp"] = int(current_dt.timestamp())
        elif format == "full":
            # 包含多种格式的完整信息
            result["iso"] = current_dt.isoformat()
            result["date_ymd"] = current_dt.strftime("%Y-%m-%d")
            result["date_dmy"] = current_dt.strftime("%d/%m/%Y")
            result["time_24h"] = current_dt.strftime("%H:%M:%S")
            result["time_12h"] = current_dt.strftime("%I:%M:%S %p")
            result["weekday"] = current_dt.strftime("%A")
            result["weekday_short"] = current_dt.strftime("%a")
            result["timestamp"] = int(current_dt.timestamp())
            result["timezone"] = current_dt.astimezone().tzinfo.tzname(current_dt)
        else:
            # 默认为ISO格式
            result["datetime"] = current_dt.isoformat()
            
        # 如果需要返回未来日期
        if return_future_dates and return_future_dates.lower() == "true":
            try:
                days = int(future_days)
                future_dates = []
                
                for i in range(1, days + 1):
                    future_dt = current_dt + timedelta(days=i)
                    if format == "iso":
                        future_dates.append(future_dt.isoformat())
                    elif format == "slash":
                        future_dates.append(future_dt.strftime("%Y/%m/%d"))
                    elif format == "chinese":
                        future_dates.append(future_dt.strftime("%Y年%m月%d日"))
                    elif format == "timestamp":
                        future_dates.append(int(future_dt.timestamp()))
                    else:
                        future_dates.append(future_dt.strftime("%Y-%m-%d"))
                
                result["future_dates"] = future_dates
            except Exception as e:
                result["error_future_dates"] = f"计算未来日期时出错: {str(e)}"
            
        return result
    
    except Exception as e:
        return {"error": f"处理时间请求时出错: {str(e)}"}

@mcp.tool()
async def search_google(
    q: str,
    device: str = "desktop",
    location: str = None,
    uule: str = None,
    google_domain: str = "google.com",
    gl: str = "us",
    hl: str = "en",
    lr: str = None,
    cr: str = None,
    nfpr: str = "0",
    filter: str = "1",
    safe: str = "off",
    time_period: str = None,
    time_period_min: str = None,
    time_period_max: str = None,
    num: str = "10",
    page: str = "1"
) -> Dict[str, Any]:
    """执行Google搜索"""
    params = {
        "engine": "google",
        "q": q,
        "device": device,
        "google_domain": google_domain,
        "gl": gl,
        "hl": hl,
        "nfpr": nfpr,
        "filter": filter,
        "safe": safe,
        "num": num,
        "page": page
    }
    
    # 添加可选参数
    optional_params = {
        "location": location,
        "uule": uule,
        "lr": lr,
        "cr": cr,
        "time_period": time_period,
        "time_period_min": time_period_min,
        "time_period_max": time_period_max
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

@mcp.tool()
async def search_google_videos(
    q: str,
    device: str = "desktop",
    location: str = None,
    uule: str = None,
    google_domain: str = "google.com",
    gl: str = "us",
    hl: str = "en",
    lr: str = None,
    cr: str = None,
    nfpr: str = "0",
    filter: str = "1",
    safe: str = "off",
    time_period: str = None,
    time_period_min: str = None,
    time_period_max: str = None,
    num: str = "10",
    page: str = "1"
) -> Dict[str, Any]:
    """执行Google视频搜索"""
    params = {
        "engine": "google_videos",
        "q": q,
        "device": device,
        "google_domain": google_domain,
        "gl": gl,
        "hl": hl,
        "nfpr": nfpr,
        "filter": filter,
        "safe": safe,
        "num": num,
        "page": page
    }
    
    # 添加可选参数
    optional_params = {
        "location": location,
        "uule": uule,
        "lr": lr,
        "cr": cr,
        "time_period": time_period,
        "time_period_min": time_period_min,
        "time_period_max": time_period_max
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    
    return await make_searchapi_request(params)

# 如果此脚本被直接运行
if __name__ == "__main__":
    print("SearchAPI MCP 服务器已启动")
    mcp.run() 