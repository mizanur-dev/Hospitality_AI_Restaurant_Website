# chat_assistant/openai_utils.py
import os
import re
import hashlib

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def sanitize_response(text: str) -> str:
    """
    Clean response text by removing markdown, LaTeX, and other formatting artifacts.
    Ensures the output is natural, human-readable text.
    """
    if not text:
        return text
    
    # Remove LaTeX-style commands: \text{...}, \frac{...}, \left, \right, etc.
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'\1 divided by \2', text)
    text = re.sub(r'\\left[(\[\{]', '', text)
    text = re.sub(r'\\right[)\]\}]', '', text)
    text = re.sub(r'\\times', 'times', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)  # Remove any remaining backslash commands
    
    # Remove markdown bold: **text** -> text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Remove markdown italic: *text* or _text_ -> text
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)
    
    # Remove markdown headers: ## Header -> Header
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove markdown code blocks and inline code
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Replace bullet point symbols with dashes
    text = re.sub(r'^[•◦▪]\s*', '- ', text, flags=re.MULTILINE)
    
    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up extra spaces
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def extract_kpi_data(prompt: str) -> dict:
    """Extract KPI data from user prompt using regex patterns."""
    import urllib.parse
    import logging
    
    logger = logging.getLogger(__name__)

    data = {}
    # Decode URL encoding if present
    decoded_prompt = urllib.parse.unquote(prompt)
    
    logger.debug(f"Extracting KPI data from: {decoded_prompt}")

    # Find all dollar amounts first (e.g., $50,000 or $14,000)
    dollar_matches = re.findall(r'\$([0-9,]+(?:\.[0-9]+)?)', decoded_prompt)
    dollar_values = []
    for val in dollar_matches:
        try:
            dollar_values.append(float(val.replace(',', '')))
        except ValueError:
            continue
    
    logger.debug(f"Dollar values found: {dollar_values}")

    # Find all numbers (including those with commas, but not already captured as dollars)
    number_matches = re.findall(r'(?<!\$)([0-9,]+(?:\.[0-9]+)?)', decoded_prompt)
    number_values = []
    for val in number_matches:
        if val and val.strip() and val not in [m.replace(',', '') for m in dollar_matches]:
            try:
                num = float(val.replace(',', ''))
                # Filter out very small numbers that are likely not KPI data (like single digits in text)
                if num >= 1:
                    number_values.append(num)
            except ValueError:
                continue

    # Combine dollar values with other numbers, prioritizing dollar values
    all_values = dollar_values + number_values
    
    logger.debug(f"All values found: {all_values}")
    # Try to detect and parse CSV/TSV/whitespace-separated blocks in the prompt (headers + values)
    csv_parsed = False
    try:
        # known header variants we care about
        csv_headers_of_interest = {
            'revenue_target', 'revenue_target_total', 'budget_total', 'budget_total_sum',
            'marketing_spend', 'marketing_spend_sum', 'target_roi', 'timeline_months',
            'acquisition_cost', 'conversion_rate',
            'market_size', 'market_share', 'competition_level', 'investment_budget',
            'growth_potential', 'market_penetration'
        }

        def normalize_header(h: str) -> str:
            h0 = re.sub(r"[^a-z0-9_ ]", '', h.lower()).strip().replace(' ', '_')
            # common truncated/typo mappings and loose prefix matches
            if h0.startswith('market_si') or h0.startswith('market_s'):
                return 'market_size'
            if h0.startswith('market_sh') or h0.startswith('market_share'):
                return 'market_share'
            if h0.startswith('competition') or h0.startswith('competiti'):
                return 'competition_level'
            if 'invest' in h0 or h0.startswith('investment'):
                return 'investment_budget'
            if 'growth' in h0 and 'potential' in h0:
                return 'growth_potential'
            if h0.startswith('market_pe') or 'penetr' in h0:
                return 'market_penetration'
            if h0.startswith('target_roi') or (('roi' in h0) and ('target' in h0 or h0.startswith('target'))):
                return 'target_roi'
            if h0.startswith('revenue') or h0.startswith('revenue_t'):
                return 'revenue_target'
            if h0.startswith('budget') or h0.startswith('budget_t'):
                return 'budget_total'
            if 'marketing' in h0:
                return 'marketing_spend'
            if h0.startswith('acquisit') or 'acquisit' in h0:
                return 'acquisition_cost'
            if 'conversion' in h0:
                return 'conversion_rate'
            if 'timeline' in h0 or 'months' in h0 or h0.startswith('timeline_r'):
                return 'timeline_months'
            return h0

        lines = decoded_prompt.strip().splitlines()
        def _safe_split(text, sep_pattern):
            """Safely split `text` by regex `sep_pattern`. Fall back to simple split on common separators when regex fails."""
            import re as _re
            try:
                return [p for p in _re.split(sep_pattern, text) if p is not None]
            except _re.error:
                # fallback heuristics
                if ',' in sep_pattern:
                    return [p.strip() for p in text.split(',')]
                if '\\t' in sep_pattern or '\t' in sep_pattern:
                    return [p.strip() for p in text.split('\t')]
                try:
                    return [p for p in _re.split(r'\s+', text) if p is not None]
                except Exception:
                    return [p.strip() for p in text.split()]
        for i in range(len(lines)):
            header_line = lines[i]
            # detect separator: comma, tab, or multiple whitespace
            sep = None
            if ',' in header_line:
                sep = r',\s*'
            elif '\t' in header_line:
                sep = '\\t'
            else:
                # if header has multiple spaces between tokens, treat as whitespace-separated
                if len(re.findall(r'\s{2,}', header_line)) >= 1:
                    sep = r'\s{2,}'

            # Fallback: if no explicit separator found, check for single-space separated headers
            # (some CSV exports or screenshots use single spaces between truncated tokens)
            if not sep:
                tokens = re.split(r'\s+', header_line.strip())
                if len(tokens) >= 3:
                    # normalize tokens and count interest headers
                    normalized = [normalize_header(t) for t in tokens if t.strip()]
                    matches = sum(1 for t in normalized if t in csv_headers_of_interest)
                    # require at least two matches to consider this a header row
                    if matches >= 2:
                        sep = r'\s+'
                    else:
                        # not a header-like line
                        sep = None

            if not sep:
                continue

            headers_raw = [h.strip() for h in _safe_split(header_line, sep)]
            headers = [normalize_header(h) for h in headers_raw if h.strip()]
            if not headers:
                continue

            if any(h in csv_headers_of_interest for h in headers):
                if i + 1 < len(lines):
                    values_line = lines[i+1]
                    values = [v.strip() for v in _safe_split(values_line, sep)]
                else:
                    values = []
                # Zip headers to values, but allow missing value row (assign empty string)
                for idx, h in enumerate(headers):
                    v = values[idx] if idx < len(values) else ''
                    v_clean = re.sub(r'[^0-9\.\-]', '', v)
                    if v_clean:
                        try:
                            num = float(v_clean)
                            data[h] = num
                        except Exception:
                            data[h] = v
                    else:
                        # preserve header presence even if value missing
                        data[h] = v
                csv_parsed = True
                # determine detected analysis type by required columns
                business_required = {'revenue_target', 'budget_total'}
                growth_required = {'market_size', 'market_share', 'investment_budget'}
                business_count = sum(1 for k in business_required if k in data)
                growth_count = sum(1 for k in growth_required if k in data)
                # Prioritize business if its required fields are present
                if business_count >= len(business_required) and growth_count < len(growth_required):
                    data['detected_analysis_type'] = 'business'
                elif growth_count >= len(growth_required) and business_count < len(business_required):
                    data['detected_analysis_type'] = 'growth'
                else:
                    # if both present, pick the one with more matching keys
                    if business_count > growth_count:
                        data['detected_analysis_type'] = 'business'
                    elif growth_count > business_count:
                        data['detected_analysis_type'] = 'growth'
                    else:
                        # ambiguous: leave unset (frontend forced marker can decide)
                        pass
                logger.debug(f"Parsed CSV block headers: {headers}, values: {values}, detected: {data.get('detected_analysis_type')}")
                break
    except Exception:
        pass

    # Simple keyword-based extraction
    prompt_lower = decoded_prompt.lower()

    # Extract total sales - look for explicit patterns first
    # Pattern handles: "total sales are $50,000" or "sales: 50000" or "my sales are $50,000"
    sales_match = re.search(r'(?:total\s+)?sales\s+(?:are|is|of|:)?\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if sales_match:
        try:
            data['total_sales'] = float(sales_match.group(1).replace(',', ''))
            logger.debug(f"Sales extracted via regex: {data['total_sales']}")
        except Exception:
            pass
    elif not csv_parsed and any(word in prompt_lower for word in ['sales', 'revenue', 'total']) and all_values:
        # Fall back to first dollar value if "sales" mentioned and not a parsed CSV
        data['total_sales'] = all_values[0]
        logger.debug(f"Sales extracted via fallback: {data['total_sales']}")

    # Extract food cost - look for explicit patterns with $ sign support
    # Pattern handles: "food cost is $14,000" or "food cost: 14000"
    food_match = re.search(r'food\s+cost\s+(?:is|are|of|:)?\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if food_match:
        data['food_cost'] = float(food_match.group(1).replace(',', ''))
        logger.debug(f"Food cost extracted via regex: {data['food_cost']}")
    elif 'food cost' in prompt_lower and len(all_values) > 1:
        # Food cost is likely the second dollar value when mentioned
        data['food_cost'] = all_values[1]
        logger.debug(f"Food cost extracted via fallback (second value): {data['food_cost']}")
    elif 'food' in prompt_lower and 'cost' in prompt_lower and len(all_values) > 1:
        data['food_cost'] = all_values[1]
        logger.debug(f"Food cost extracted via keyword fallback: {data['food_cost']}")
    # Also try to match just "food" followed by a dollar amount if not already found
    elif 'food_cost' not in data and 'food' in prompt_lower:
        food_alt_match = re.search(r'food[^0-9]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if food_alt_match:
            data['food_cost'] = float(food_alt_match.group(1).replace(',', ''))
            logger.debug(f"Food cost extracted via alt pattern: {data['food_cost']}")
    
    logger.debug(f"Final extracted data: {data}")

    # Extract labor cost - look for explicit patterns with $ sign support
    labor_match = re.search(r'labor\s+cost\s+(?:is|are|of|:)?\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if labor_match:
        data['labor_cost'] = float(labor_match.group(1).replace(',', ''))
    elif 'labor cost' in prompt_lower and len(all_values) > 1:
        data['labor_cost'] = all_values[1] if 'food_cost' not in data else (all_values[2] if len(all_values) > 2 else all_values[1])
    elif 'labor' in prompt_lower and len(all_values) > 1:
        data['labor_cost'] = all_values[1] if 'food_cost' not in data else (all_values[2] if len(all_values) > 2 else None)

    # Extract hours worked - look for "hours worked: NUMBER" or "NUMBER hours"
    # First try "hours worked: NUMBER" pattern (more specific)
    hours_match = re.search(r'hours\s+worked[:\s]+(\d+(?:,\d+)?)', prompt_lower)
    if hours_match:
        data['hours_worked'] = float(hours_match.group(1).replace(',', ''))
    else:
        # Try "NUMBER hours" pattern (but not "overtime hours")
        hours_match2 = re.search(r'(?<!overtime\s)(\d+(?:,\d+)?)\s*hours?(?!\s*:)', prompt_lower)
        if hours_match2:
            data['hours_worked'] = float(hours_match2.group(1).replace(',', ''))
        else:
            # Try "hours: NUMBER" pattern
            hours_match3 = re.search(r'(?<!overtime\s)hours?[:\s]+(\d+(?:,\d+)?)', prompt_lower)
            if hours_match3:
                data['hours_worked'] = float(hours_match3.group(1).replace(',', ''))
            elif any(word in prompt_lower for word in ['hours', 'hour']):
                # Find the largest number that could be hours (fallback)
                for num in sorted(number_values, reverse=True):
                    if num > 0 and num < 1000:  # Reasonable range for hours
                        data['hours_worked'] = num
                        break

    # =====================================================
    # OPTIONAL KPI PARAMETERS - Labor Cost Analysis
    # =====================================================
    
    # Extract overtime hours - patterns: "overtime hours: 40", "40 overtime hours", "overtime: 40"
    # First try "overtime hours: NUMBER" pattern (most specific for new format)
    overtime_match = re.search(r'overtime\s+hours?[:\s]+(\d+(?:,\d+)?)', prompt_lower)
    if overtime_match:
        data['overtime_hours'] = float(overtime_match.group(1).replace(',', ''))
    else:
        # Try "NUMBER overtime hours" pattern
        overtime_match2 = re.search(r'(\d+(?:,\d+)?)\s*overtime\s*hours?', prompt_lower)
        if overtime_match2:
            data['overtime_hours'] = float(overtime_match2.group(1).replace(',', ''))
        else:
            # Try "overtime: NUMBER" pattern
            overtime_match3 = re.search(r'overtime[:\s]+(\d+(?:,\d+)?)', prompt_lower)
            if overtime_match3:
                data['overtime_hours'] = float(overtime_match3.group(1).replace(',', ''))
            else:
                # Try "includes NUMBER overtime" pattern
                overtime_match4 = re.search(r'includes?\s+(\d+(?:,\d+)?)\s*(?:overtime|ot)', prompt_lower)
                if overtime_match4:
                    data['overtime_hours'] = float(overtime_match4.group(1).replace(',', ''))
    
    # Extract covers (guests served) - patterns: "covers served: 2,000", "2,000 covers", "served 2000 guests"
    # First try "covers served: NUMBER" pattern (most specific for new format)
    covers_match = re.search(r'covers?\s+served[:\s]+(\d+(?:,\d+)?)', prompt_lower)
    if covers_match:
        data['covers'] = int(float(covers_match.group(1).replace(',', '')))
    else:
        # Try "NUMBER covers" pattern
        covers_match2 = re.search(r'(\d+(?:,\d+)?)\s*covers?', prompt_lower)
        if covers_match2:
            data['covers'] = int(float(covers_match2.group(1).replace(',', '')))
        else:
            # Try "served NUMBER guests/customers/covers" pattern
            covers_match3 = re.search(r'served\s+(\d+(?:,\d+)?)\s*(?:guests?|customers?|covers?)?', prompt_lower)
            if covers_match3:
                data['covers'] = int(float(covers_match3.group(1).replace(',', '')))
            else:
                # Try "guests/customers: NUMBER" pattern
                covers_match4 = re.search(r'(?:guests?|customers?)[:\s]+(\d+(?:,\d+)?)', prompt_lower)
                if covers_match4:
                    data['covers'] = int(float(covers_match4.group(1).replace(',', '')))
    
    # =====================================================
    # OPTIONAL KPI PARAMETERS - Food Cost Analysis
    # =====================================================
    
    # Extract waste cost - patterns: "waste cost: $800", "waste cost is $800", "waste: $800"
    waste_cost_match = re.search(r'waste\s+cost[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if waste_cost_match:
        data['waste_cost'] = float(waste_cost_match.group(1).replace(',', ''))
    else:
        waste_match2 = re.search(r'waste\s+cost\s+(?:is|are|of)\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if waste_match2:
            data['waste_cost'] = float(waste_match2.group(1).replace(',', ''))
        else:
            waste_match3 = re.search(r'waste[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
            if waste_match3:
                data['waste_cost'] = float(waste_match3.group(1).replace(',', ''))
    
    # Extract beginning inventory - patterns: "beginning inventory: $5,000", "beginning inventory was $5,000"
    begin_inv_match = re.search(r'(?:beginning|starting|start)\s+inventory[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if begin_inv_match:
        data['beginning_inventory'] = float(begin_inv_match.group(1).replace(',', ''))
    else:
        begin_inv_match2 = re.search(r'(?:beginning|starting|start)\s+inventory\s+(?:is|was|of)\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if begin_inv_match2:
            data['beginning_inventory'] = float(begin_inv_match2.group(1).replace(',', ''))
    
    # Extract ending inventory - patterns: "ending inventory: $4,500", "ending inventory is $4,500"
    end_inv_match = re.search(r'(?:ending|end|final)\s+inventory[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if end_inv_match:
        data['ending_inventory'] = float(end_inv_match.group(1).replace(',', ''))
    else:
        end_inv_match2 = re.search(r'(?:ending|end|final)\s+inventory\s+(?:is|was|of)\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if end_inv_match2:
            data['ending_inventory'] = float(end_inv_match2.group(1).replace(',', ''))
    
    # =====================================================
    # OPTIONAL KPI PARAMETERS - Sales Performance Analysis
    # =====================================================
    
    # Extract previous sales - patterns: "previous sales: $48,000", "previous sales were $48,000"
    prev_sales_match = re.search(r'previous\s+(?:period\s+)?sales[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if prev_sales_match:
        data['previous_sales'] = float(prev_sales_match.group(1).replace(',', ''))
    else:
        prev_match2 = re.search(r'previous\s+(?:period\s+)?sales\s+(?:were|was|is|of)\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if prev_match2:
            data['previous_sales'] = float(prev_match2.group(1).replace(',', ''))
        else:
            prev_match3 = re.search(r'last\s+(?:period|month|week)\s+(?:sales\s+)?(?:were|was|is|of|:)?\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
            if prev_match3:
                data['previous_sales'] = float(prev_match3.group(1).replace(',', ''))
    
    # Extract average check - patterns: "average check: $25", "average check of $25", "avg check: 25"
    avg_check_match = re.search(r'(?:average|avg)\s+check[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if avg_check_match:
        data['avg_check'] = float(avg_check_match.group(1).replace(',', ''))
    else:
        avg_check_match2 = re.search(r'(?:average|avg)\s+check\s+(?:is|of)\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if avg_check_match2:
            data['avg_check'] = float(avg_check_match2.group(1).replace(',', ''))

    # Extract hourly rate - look for "rate" or "hourly" followed by a number
    rate_match = re.search(r'(?:hourly\s+)?rate[:\s]*([0-9,]+)', prompt_lower)
    if rate_match:
        data['hourly_rate'] = float(rate_match.group(1).replace(',', ''))
    else:
        # Use second dollar value if it's in reasonable range
        for val in number_values[1:]:  # Skip first value (sales)
            if 10 <= val <= 100:  # Reasonable range for hourly rates
                data['hourly_rate'] = val
                break

    # Extract HR-specific metrics
    # Turnover rate
    turnover_match = re.search(r'turnover[_\s]+rate[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if turnover_match:
        turnover_value = float(turnover_match.group(1).replace(',', ''))
        data['turnover_rate'] = turnover_value * 100 if 0 < turnover_value <= 1 else turnover_value
    elif 'turnover' in prompt_lower and number_values:
        # Use first number if turnover is mentioned
        data['turnover_rate'] = number_values[0]

    # Industry average
    industry_match = re.search(r'industry[_\s]+(?:average|avg)[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if industry_match:
        industry_value = float(industry_match.group(1).replace(',', ''))
        data['industry_average'] = industry_value * 100 if 0 < industry_value <= 1 else industry_value

    # Performance metrics
    satisfaction_match = re.search(r'customer[_\s]+satisfaction[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if satisfaction_match:
        satisfaction_value = float(satisfaction_match.group(1).replace(',', ''))
        data['customer_satisfaction'] = satisfaction_value * 100 if 0 < satisfaction_value <= 1 else satisfaction_value

    performance_match = re.search(r'sales[_\s]+performance[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if performance_match:
        performance_value = float(performance_match.group(1).replace(',', ''))
        data['sales_performance'] = performance_value * 100 if 0 < performance_value <= 1 else performance_value

    efficiency_match = re.search(r'efficiency[_\s]+score[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if efficiency_match:
        efficiency_value = float(efficiency_match.group(1).replace(',', ''))
        data['efficiency_score'] = efficiency_value * 100 if 0 < efficiency_value <= 1 else efficiency_value

    attendance_match = re.search(r'attendance[_\s]+rate[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if attendance_match:
        attendance_value = float(attendance_match.group(1).replace(',', ''))
        data['attendance_rate'] = attendance_value * 100 if 0 < attendance_value <= 1 else attendance_value

    # Extract Beverage Management metrics
    # Liquor cost metrics
    expected_oz_match = re.search(r'expected\s+(?:oz|ounces?)[:\s]*([0-9,]+)', prompt_lower)
    if expected_oz_match:
        data['expected_oz'] = float(expected_oz_match.group(1).replace(',', ''))

    actual_oz_match = re.search(r'actual\s+(?:oz|ounces?)[:\s]*([0-9,]+)', prompt_lower)
    if actual_oz_match:
        data['actual_oz'] = float(actual_oz_match.group(1).replace(',', ''))

    liquor_cost_match = re.search(r'liquor\s+cost[:\s]*([0-9,]+)', prompt_lower)
    if liquor_cost_match:
        data['liquor_cost'] = float(liquor_cost_match.group(1).replace(',', ''))

    # Inventory metrics
    current_stock_match = re.search(r'current\s+stock[:\s]*([0-9,]+)', prompt_lower)
    if current_stock_match:
        data['current_stock'] = float(current_stock_match.group(1).replace(',', ''))

    reorder_point_match = re.search(r'reorder\s+point[:\s]*([0-9,]+)', prompt_lower)
    if reorder_point_match:
        data['reorder_point'] = float(reorder_point_match.group(1).replace(',', ''))

    monthly_usage_match = re.search(r'monthly\s+usage[:\s]*([0-9,]+)', prompt_lower)
    if monthly_usage_match:
        data['monthly_usage'] = float(monthly_usage_match.group(1).replace(',', ''))

    inventory_value_match = re.search(r'inventory\s+value[:\s]*([0-9,]+)', prompt_lower)
    if inventory_value_match:
        data['inventory_value'] = float(inventory_value_match.group(1).replace(',', ''))

    # Pricing metrics
    drink_price_match = re.search(r'drink\s+price[:\s]*([0-9,]+)', prompt_lower)
    if drink_price_match:
        data['drink_price'] = float(drink_price_match.group(1).replace(',', ''))

    cost_per_drink_match = re.search(r'cost\s+per\s+drink[:\s]*([0-9,]+)', prompt_lower)
    if cost_per_drink_match:
        data['cost_per_drink'] = float(cost_per_drink_match.group(1).replace(',', ''))

    sales_volume_match = re.search(r'sales\s+volume[:\s]*([0-9,]+)', prompt_lower)
    if sales_volume_match:
        data['sales_volume'] = float(sales_volume_match.group(1).replace(',', ''))

    competitor_price_match = re.search(r'competitor\s+price[:\s]*([0-9,]+)', prompt_lower)
    if competitor_price_match:
        data['competitor_price'] = float(competitor_price_match.group(1).replace(',', ''))

    # Extract Menu Engineering metrics
    # Product mix metrics
    item_sales_match = re.search(r'item\s+sales[:\s]*([0-9,]+)', prompt_lower)
    if item_sales_match:
        data['item_sales'] = float(item_sales_match.group(1).replace(',', ''))

    item_cost_match = re.search(r'item\s+cost[:\s]*([0-9,]+)', prompt_lower)
    if item_cost_match:
        data['item_cost'] = float(item_cost_match.group(1).replace(',', ''))

    item_profit_match = re.search(r'item\s+profit[:\s]*([0-9,]+)', prompt_lower)
    if item_profit_match:
        data['item_profit'] = float(item_profit_match.group(1).replace(',', ''))

    item_price_match = re.search(r'item\s+price[:\s]*([0-9,]+)', prompt_lower)
    if item_price_match:
        data['item_price'] = float(item_price_match.group(1).replace(',', ''))

    # Menu design metrics
    menu_items_match = re.search(r'menu\s+items[:\s]*([0-9,]+)', prompt_lower)
    if menu_items_match:
        data['menu_items'] = float(menu_items_match.group(1).replace(',', ''))

    high_profit_items_match = re.search(r'high\s+profit\s+items[:\s]*([0-9,]+)', prompt_lower)
    if high_profit_items_match:
        data['high_profit_items'] = float(high_profit_items_match.group(1).replace(',', ''))

    sales_distribution_match = re.search(r'sales\s+distribution[:\s]*([0-9,]+)', prompt_lower)
    if sales_distribution_match:
        data['sales_distribution'] = float(sales_distribution_match.group(1).replace(',', ''))

    visual_hierarchy_match = re.search(r'visual\s+hierarchy[:\s]*([0-9,]+)', prompt_lower)
    if visual_hierarchy_match:
        data['visual_hierarchy'] = float(visual_hierarchy_match.group(1).replace(',', ''))

    # Extract Recipe Management metrics
    # Recipe costing metrics (support both space and underscore variants)
    ingredient_cost_match = re.search(r'(?:ingredient[\s_]+cost)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', decoded_prompt, re.IGNORECASE)
    if ingredient_cost_match:
        try:
            data['ingredient_cost'] = float(ingredient_cost_match.group(1).replace(',', ''))
        except Exception:
            pass

    portion_cost_match = re.search(r'(?:portion[\s_]+cost)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', decoded_prompt, re.IGNORECASE)
    if portion_cost_match:
        try:
            data['portion_cost'] = float(portion_cost_match.group(1).replace(',', ''))
        except Exception:
            pass

    recipe_price_match = re.search(r'(?:recipe[\s_]+price)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', decoded_prompt, re.IGNORECASE)
    if recipe_price_match:
        try:
            data['recipe_price'] = float(recipe_price_match.group(1).replace(',', ''))
        except Exception:
            pass

    # Optional recipe fields
    labor_cost_match_recipe = re.search(r'(?:labor[\s_]+cost)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', decoded_prompt, re.IGNORECASE)
    if labor_cost_match_recipe and 'labor_cost' not in data:
        try:
            data['labor_cost'] = float(labor_cost_match_recipe.group(1).replace(',', ''))
        except Exception:
            pass

    servings_match = re.search(r'(?:servings?)[:\s]*([0-9]+(?:\.[0-9]+)?)', decoded_prompt, re.IGNORECASE)
    if servings_match:
        try:
            data['servings'] = float(servings_match.group(1).replace(',', ''))
        except Exception:
            pass


    # Recipe scaling: detect patterns like "serves 6 to 48 servings" or "6 to 48 servings"
    scale_match = re.search(r'(?:serves|servings?)\s*([0-9]+)\s*(?:to|\-+)\s*([0-9]+)\s*(?:servings?)', decoded_prompt, re.IGNORECASE)
    if not scale_match:
        # Alternate phrasing: "Scale ... 6 to 48 servings"
        scale_match = re.search(r'([0-9]+)\s*(?:to|\-+)\s*([0-9]+)\s*(?:servings?)', decoded_prompt, re.IGNORECASE)
    if scale_match:
        try:
            data['current_batch'] = float(scale_match.group(1).replace(',', ''))
            data['target_batch'] = float(scale_match.group(2).replace(',', ''))
        except Exception:
            pass

    # Recipe name: support quoted and unquoted after recipe_name or recipe name
    recipe_name_match = re.search(r'(?:recipe[\s_]*name)[:\s]*"([^"]+)"', decoded_prompt, re.IGNORECASE)
    if not recipe_name_match:
        recipe_name_match = re.search(r'(?:recipe[\s_]*name)[:\s]*([A-Za-z0-9 &\'"\-\.]+)', decoded_prompt, re.IGNORECASE)
    if recipe_name_match:
        try:
            name_val = recipe_name_match.group(1).strip()
            if name_val:
                data['recipe_name'] = name_val
        except Exception:
            pass

    # Ingredient optimization metrics
    current_cost_match = re.search(r'current\s+cost[:\s]*([0-9,]+)', prompt_lower)
    if current_cost_match:
        data['current_cost'] = float(current_cost_match.group(1).replace(',', ''))

    supplier_cost_match = re.search(r'supplier\s+cost[:\s]*([0-9,]+)', prompt_lower)
    if supplier_cost_match:
        data['supplier_cost'] = float(supplier_cost_match.group(1).replace(',', ''))

    waste_percentage_match = re.search(r'waste\s+percentage[:\s]*([0-9,]+)', prompt_lower)
    if waste_percentage_match:
        data['waste_percentage'] = float(waste_percentage_match.group(1).replace(',', ''))

    quality_score_match = re.search(r'quality\s+score[:\s]*([0-9,]+)', prompt_lower)
    if quality_score_match:
        data['quality_score'] = float(quality_score_match.group(1).replace(',', ''))

    # Recipe scaling metrics
    current_batch_match = re.search(r'current\s+batch[:\s]*([0-9,]+)', prompt_lower)
    if current_batch_match:
        data['current_batch'] = float(current_batch_match.group(1).replace(',', ''))

    target_batch_match = re.search(r'target\s+batch[:\s]*([0-9,]+)', prompt_lower)
    if target_batch_match:
        data['target_batch'] = float(target_batch_match.group(1).replace(',', ''))

    yield_percentage_match = re.search(r'yield\s+percentage[:\s]*([0-9,]+)', prompt_lower)
    if yield_percentage_match:
        data['yield_percentage'] = float(yield_percentage_match.group(1).replace(',', ''))

    consistency_score_match = re.search(r'consistency\s+score[:\s]*([0-9,]+)', prompt_lower)
    if consistency_score_match:
        data['consistency_score'] = float(consistency_score_match.group(1).replace(',', ''))

    # Extract Strategic Planning metrics
    # Sales forecasting metrics (allow $, commas, decimals and % for growth)
    historical_sales_match = re.search(r'historical\s+sales[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if historical_sales_match:
        data['historical_sales'] = float(historical_sales_match.group(1).replace(',', ''))

    current_sales_match = re.search(r'current\s+sales[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if current_sales_match:
        data['current_sales'] = float(current_sales_match.group(1).replace(',', ''))

    growth_rate_match = re.search(r'growth\s+rate[:\s]*([0-9]+(?:\.[0-9]+)?)%?', prompt_lower)
    if growth_rate_match:
        data['growth_rate'] = float(growth_rate_match.group(1))

    seasonal_factor_match = re.search(r'seasonal\s+factor[:\s]*([0-9]+(?:\.[0-9]+)?)', prompt_lower)
    if seasonal_factor_match:
        data['seasonal_factor'] = float(seasonal_factor_match.group(1))

    # Growth strategy metrics (allow $, commas, decimals and %)
    market_size_match = re.search(r'market\s+size[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if market_size_match:
        data['market_size'] = float(market_size_match.group(1).replace(',', ''))

    market_share_match = re.search(r'market\s+share[:\s]*([0-9]+(?:\.[0-9]+)?)%?', prompt_lower)
    if market_share_match:
        data['market_share'] = float(market_share_match.group(1))

    competition_level_match = re.search(r'competition\s+level[:\s]*([0-9]+(?:\.[0-9]+)?)%?', prompt_lower)
    if competition_level_match:
        data['competition_level'] = float(competition_level_match.group(1))

    investment_budget_match = re.search(r'investment\s+budget[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if investment_budget_match:
        data['investment_budget'] = float(investment_budget_match.group(1).replace(',', ''))

    # Business Goals / Strategic Targets extraction (CSV-friendly headers)
    revenue_target_match = re.search(r'revenue[_ ]?target(?:[_\w]*)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if 'revenue_target' not in data and revenue_target_match:
        try:
            data['revenue_target'] = float(revenue_target_match.group(1).replace(',', ''))
        except Exception:
            pass

    budget_total_match = re.search(r'budget(?:[_\w]*)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if 'budget_total' not in data and budget_total_match:
        try:
            data['budget_total'] = float(budget_total_match.group(1).replace(',', ''))
        except Exception:
            pass

    marketing_spend_match = re.search(r'marketing[_ ]?spend(?:[_\w]*)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if 'marketing_spend' not in data and marketing_spend_match:
        try:
            data['marketing_spend'] = float(marketing_spend_match.group(1).replace(',', ''))
        except Exception:
            pass

    target_roi_match = re.search(r'(?:target[_ ]?roi|average[_ ]?target[_ ]?roi|target roi|average_target_roi_percent)[:\s]*([0-9]+(?:\.[0-9]+)?)%?', prompt_lower)
    if 'target_roi' not in data and target_roi_match:
        try:
            data['target_roi'] = float(target_roi_match.group(1))
        except Exception:
            pass

    timeline_months_match = re.search(r'(?:timeline[_ ]?months|timeline|timeline_months)[:\s]*([0-9,]+)', prompt_lower)
    if 'timeline_months' not in data and timeline_months_match:
        try:
            data['timeline_months'] = int(float(timeline_months_match.group(1)))
        except Exception:
            pass

    # Customer acquisition metrics
    acquisition_cost_match = re.search(r'acquisition[_ ]?cost[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if 'acquisition_cost' not in data and acquisition_cost_match:
        try:
            data['acquisition_cost'] = float(acquisition_cost_match.group(1).replace(',', ''))
        except Exception:
            pass

    conversion_rate_match = re.search(r'conversion[_ ]?rate[:\s]*([0-9]+(?:\.[0-9]+)?)%?', prompt_lower)
    if 'conversion_rate' not in data and conversion_rate_match:
        try:
            data['conversion_rate'] = float(conversion_rate_match.group(1))
        except Exception:
            pass

    # Operational excellence metrics
    efficiency_score_match = re.search(r'efficiency\s+score[:\s]*([0-9,]+)', prompt_lower)
    if efficiency_score_match:
        data['efficiency_score'] = float(efficiency_score_match.group(1).replace(',', ''))

    process_time_match = re.search(r'process\s+time[:\s]*([0-9,]+)', prompt_lower)
    if process_time_match:
        data['process_time'] = float(process_time_match.group(1).replace(',', ''))

    quality_rating_match = re.search(r'quality\s+rating[:\s]*([0-9,]+)', prompt_lower)
    if quality_rating_match:
        data['quality_rating'] = float(quality_rating_match.group(1).replace(',', ''))

    customer_satisfaction_match = re.search(r'customer[_\s]+satisfaction[:\s]*([0-9,]+(?:\.[0-9]+)?)%?', prompt_lower)
    if customer_satisfaction_match:
        customer_satisfaction_value = float(customer_satisfaction_match.group(1).replace(',', ''))
        data['customer_satisfaction'] = customer_satisfaction_value * 100 if 0 < customer_satisfaction_value <= 1 else customer_satisfaction_value

    # Extract KPI Dashboard metrics
    # Comprehensive analysis metrics (support $ and common phrasing)
    prime_cost_match = re.search(r'prime\s+cost\s+(?:is|are|of|:)?\s*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
    if prime_cost_match:
        data['prime_cost'] = float(prime_cost_match.group(1).replace(',', ''))
    # Fallback: if prime not provided but labor and food are present, compute prime = labor + food
    if 'prime_cost' not in data and 'labor_cost' in data and 'food_cost' in data:
        data['prime_cost'] = float(data['labor_cost']) + float(data['food_cost'])

    # Performance optimization metrics
    current_performance_match = re.search(r'current\s+performance[:\s]*([0-9,]+)', prompt_lower)
    if current_performance_match:
        data['current_performance'] = float(current_performance_match.group(1).replace(',', ''))

    target_performance_match = re.search(r'target\s+performance[:\s]*([0-9,]+)', prompt_lower)
    if target_performance_match:
        data['target_performance'] = float(target_performance_match.group(1).replace(',', ''))

    optimization_potential_match = re.search(r'optimization\s+potential[:\s]*([0-9,]+)', prompt_lower)
    if optimization_potential_match:
        data['optimization_potential'] = float(optimization_potential_match.group(1).replace(',', ''))

    efficiency_score_match2 = re.search(r'efficiency\s+score[:\s]*([0-9,]+)', prompt_lower)
    if efficiency_score_match2:
        data['efficiency_score'] = float(efficiency_score_match2.group(1).replace(',', ''))
    return data


def handle_kpi_analysis(prompt: str) -> str:
    """Handle KPI analysis requests by calling our specialized functions."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Import here to avoid circular imports
        from backend.consulting_services.kpi.kpi_utils import (
            calculate_labor_cost_analysis,
            calculate_prime_cost_analysis,
            calculate_sales_performance_analysis,
            calculate_kpi_summary,
            calculate_food_cost_analysis,
            format_business_report
        )
        from backend.consulting_services.inventory.tracking import calculate_inventory_variance

        data = extract_kpi_data(prompt)
        # Import task registry early so forced routing can use it
        from apps.agent_core.task_registry import task_registry

        logger.info(f"KPI Analysis - Extracted data: {data}")
        logger.info(f"KPI Analysis - Original prompt: {prompt}")

        # Allow frontend explicit forced analysis type to override CSV-detected routing for special cases
        prompt_lower = prompt.lower()
        forced_match_early = re.search(r'analysis[_ ]?type[:\s]*([a-z0-9 _-]+)', prompt_lower)
        forced_early = forced_match_early.group(1).strip() if forced_match_early else None

        # If CSV parsing detected a preferred analysis type, honor it — except when a forced marker
        # explicitly requests an alternate analysis like 'Best Way'. In that case, respect the forced marker.
        detected = data.get('detected_analysis_type')
        if detected == 'business' and forced_early and 'best' in forced_early:
            # fall through to forced handling below (do not perform business routing)
            logger.info("Detected business CSV but overridden by forced analysis type: Best Way")
        elif detected == 'business':
            try:
                rev = float(data.get('revenue_target') or data.get('revenue_target_total') or 0)
            except Exception:
                rev = 0
            try:
                bud = float(data.get('budget_total') or data.get('budget_total_sum') or 0)
            except Exception:
                bud = 0
            try:
                mkt = float(data.get('marketing_spend') or data.get('marketing_spend_sum') or 0)
            except Exception:
                mkt = 0
            try:
                roi_v = float(data.get('target_roi') or data.get('average_target_roi_percent') or 0)
            except Exception:
                roi_v = 0
            try:
                tl = int(float(data.get('timeline_months') or 12))
            except Exception:
                tl = 12

            metrics = {
                'revenue_target': rev,
                'budget_total': bud,
                'marketing_spend': mkt,
                'target_roi': roi_v,
                'timeline_months': tl
            }
            total_spend = (bud or 0) + (mkt or 0)
            projected_net = (rev or 0) - total_spend
            roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0
            performance = {'rating': 'Good' if roi_achieved >= (roi_v or 0) else 'Needs Improvement', 'roi_achieved': roi_achieved}
            recommendations = []
            if roi_achieved < (roi_v or 0):
                recommendations.append('Reduce budget or increase revenue initiatives to meet target ROI')
            if mkt > 0 and (mkt / max(total_spend, 1)) > 0.5:
                recommendations.append('Rebalance marketing spend to ensure efficient ROI')
            if rev < total_spend:
                recommendations.append('Reassess revenue assumptions; consider phased rollout to reduce upfront spend')
            if not recommendations:
                recommendations.append('Execute the plan and monitor monthly progress against KPIs')

            additional_data = {'financials': {'Total Spend': total_spend, 'Projected Net': projected_net, 'ROI Achieved': f"{roi_achieved:.1f}%"}}
            logger.info("Routing: Business Goals (CSV-detected)")
            report = format_business_report('Business Goals Analysis', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
            return report.get('business_report_html', report.get('business_report', 'Analysis completed but no report generated.'))

        if detected == 'growth':
            logger.info("Routing: Growth Strategy (CSV-detected)")
            result, status = task_registry.execute_task(service="strategic", subtask="growth_strategy", params=data)
            if result.get('status') == 'success':
                return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
            else:
                return f"Error: {result.get('error', 'Analysis failed')}"

        # normalize prompt lowercase for routing and pattern matching
        prompt_lower = prompt.lower()

        # If frontend provided an explicit analysis type marker, honor it first
        forced_match = re.search(r'analysis[_ ]?type[:\s]*([a-z0-9 _-]+)', prompt_lower)
        if forced_match:
            forced = forced_match.group(1).strip()
            logger.info(f"Forced analysis type detected: {forced}")

            # If the frontend explicitly forced recipe costing, route to recipe handler
            if any(tok in forced for tok in ['recipe', 'recipe_cost', 'recipe_costing', 'recipe-costing']):
                logger.info("Routing: Recipe Costing (forced)")
                # Ensure we have at least one recipe metric or a recipe_name to proceed.
                has_numeric_metric = any(k in data for k in ('ingredient_cost', 'portion_cost', 'recipe_price'))
                has_recipe_name = 'recipe_name' in data
                # If no numeric params or recipe name, attempt to parse inline CSV-like rows from the prompt
                if not has_numeric_metric and not has_recipe_name:
                    try:
                        import io
                        # Match rows like: Name,number,number,number[,number[,number]]
                        row_pattern = re.compile(r"([A-Za-z0-9 &'\"\-\.]+)\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*([0-9]+(?:\.[0-9]+)?)(?:\s*,\s*([0-9]+(?:\.[0-9]+)?))?(?:\s*,\s*([0-9]+(?:\.[0-9]+)?))?", re.IGNORECASE)
                        matches = list(row_pattern.finditer(prompt))
                        if matches:
                            csv_lines = ["recipe_name,ingredient_cost,portion_cost,recipe_price,servings,labor_cost"]
                            for m in matches:
                                cols = [m.group(1).strip(), m.group(2) or '', m.group(3) or '', m.group(4) or '', m.group(5) or '', m.group(6) or '']
                                csv_lines.append(','.join(str(c) for c in cols))
                            csv_text = '\n'.join(csv_lines)
                            csv_file = io.StringIO(csv_text)
                            try:
                                csv_file.name = 'inline_recipes.csv'
                            except Exception:
                                pass
                            from backend.consulting_services.recipe.analysis_functions import process_recipe_csv_data
                            outcome = process_recipe_csv_data(csv_file)
                            if outcome.get('status') == 'success':
                                s = outcome.get('summary', {})
                                top = outcome.get('top_performers', [])
                                html = f"<div><strong>Recipe Portfolio Summary</strong><br>Total Recipes: {s.get('total_recipes')} — Avg Food Cost: {s.get('avg_food_cost_percent')} — Avg Margin: {s.get('avg_profit_margin')}<br></div>"
                                if top:
                                    html += "<div style=\"margin-top:0.5rem\"><strong>Top Performers:</strong><ul>"
                                    for t in top:
                                        html += f"<li>{t.get('recipe_name')} — Price ${t.get('recipe_price')} — Margin {t.get('profit_margin')}%</li>"
                                    html += "</ul></div>"
                                html += "<div style=\"margin-top:0.5rem\"><em>Full portfolio report is available via the Recipe Management upload.</em></div>"
                                return html
                            # If parsing succeeded but processing failed, fall through to guidance below
                    except Exception as e:
                        logger.exception("Inline CSV parsing failed: %s", str(e))
                    # Helpful guidance if inline parsing not found or processing failed
                    return ("To analyze recipe costing I need either an uploaded CSV or sample recipe rows.\n\n"
                            "Required CSV columns: recipe_name, ingredient_cost, portion_cost, recipe_price\n"
                            "Optional columns: labor_cost, total_cost, servings\n\n"
                            "Example CSV (paste or upload):\n"
                            "recipe_name,ingredient_cost,portion_cost,recipe_price,servings,labor_cost\n"
                            "Classic Tomato Soup,5.50,2.00,15.00,6,3.00\n\n"
                            "Please upload your CSV using the Upload button on the Recipe Management page or paste a few sample rows into the chat, then try again.")
                try:
                    result, status = task_registry.execute_task(
                        service="recipe",
                        subtask="costing",
                        params=data
                    )
                    if result.get('status') == 'success':
                        return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                    else:
                        return f"Error: {result.get('error', 'Analysis failed')}"
                except Exception as e:
                    return f"Error: Recipe costing failed: {str(e)}"

            # Support explicit SWOT requests (parse lists and return HTML)
            if 'swot' in forced or 'strength' in forced or 'weakness' in forced:
                logger.info("Routing: SWOT Analysis (forced)")
                # Simple parser: look for 'Strengths:', 'Weaknesses:', 'Opportunities:', 'Threats:'
                def _parse_swot(text: str):
                    sections = {'strengths': [], 'weaknesses': [], 'opportunities': [], 'threats': []}
                    # split by semicolon or newline then match prefixes
                    parts = re.split(r'[;\n]+', text)
                    for p in parts:
                        p = p.strip()
                        if not p:
                            continue
                        m = re.match(r'^(strengths?)[:\s]*(.*)$', p, re.IGNORECASE)
                        if m:
                            items = re.split(r',\s*', m.group(2)) if m.group(2) else []
                            sections['strengths'].extend([it.strip() for it in items if it.strip()])
                            continue
                        m = re.match(r'^(weaknesses?)[:\s]*(.*)$', p, re.IGNORECASE)
                        if m:
                            items = re.split(r',\s*', m.group(2)) if m.group(2) else []
                            sections['weaknesses'].extend([it.strip() for it in items if it.strip()])
                            continue
                        m = re.match(r'^(opportunities?)[:\s]*(.*)$', p, re.IGNORECASE)
                        if m:
                            items = re.split(r',\s*', m.group(2)) if m.group(2) else []
                            sections['opportunities'].extend([it.strip() for it in items if it.strip()])
                            continue
                        m = re.match(r'^(threats?)[:\s]*(.*)$', p, re.IGNORECASE)
                        if m:
                            items = re.split(r',\s*', m.group(2)) if m.group(2) else []
                            sections['threats'].extend([it.strip() for it in items if it.strip()])
                            continue
                    return sections

                sw = _parse_swot(prompt)
                # Build recommendations from SWOT points (simple heuristic)
                recs = []
                if sw.get('strengths'):
                    for s in sw['strengths']:
                        recs.append(f"Leverage strength: {s} — consider programs or promotions that amplify this advantage.")
                if sw.get('weaknesses'):
                    for w in sw['weaknesses']:
                        recs.append(f"Address weakness: {w} — prioritize quick wins (process changes, staffing optimization).")
                if sw.get('opportunities'):
                    for o in sw['opportunities']:
                        recs.append(f"Pursue opportunity: {o} — run a pilot in 30-90 days to validate demand.")
                if sw.get('threats'):
                    for t in sw['threats']:
                        recs.append(f"Mitigate threat: {t} — implement monitoring and contingency plans.")

                metrics = {}
                performance = {'rating': 'Acceptable'}
                additional = {'Strengths': {str(i+1): v for i, v in enumerate(sw.get('strengths', []))},
                              'Weaknesses': {str(i+1): v for i, v in enumerate(sw.get('weaknesses', []))},
                              'Opportunities': {str(i+1): v for i, v in enumerate(sw.get('opportunities', []))},
                              'Threats': {str(i+1): v for i, v in enumerate(sw.get('threats', []))}}

                report = format_business_report('SWOT Analysis', metrics, performance, recs or ['No recommendations generated.'], benchmarks=None, additional_data=additional)
                return report.get('business_report_html', report.get('business_report', 'SWOT analysis generated.'))
            # Support explicit 'Best Way' strategic planning sequence
            if 'best' in forced and ('way' in forced or 'best way' in forced or 'best_way' in forced):
                logger.info("Routing: Best Way (forced)")
                # Build a concise strategic planning sequence using any uploaded CSV headers/values
                steps = [
                    'Define Objectives: Clarify top-level business goals and success metrics.',
                    'Audit & SWOT: Assess strengths, weaknesses, opportunities, and threats using uploaded data.',
                    'Set KPIs: Choose measurable KPIs (revenue target, conversion rate, market share).',
                    'Budget & Resources: Allocate budgets by channel and priority (use budget_total & marketing_spend).',
                    'Timeline & Milestones: Define a 3-12 month timeline with checkpoints.',
                    'Execute & Track: Implement tactics and monitor KPI cadence (weekly/monthly).',
                    'Review & Improve: Run monthly reviews and reallocate budget to top-performing initiatives.'
                ]

                # Include CSV-derived summary if available
                csv_summary = {}
                if data:
                    # pick some common fields if present
                    for k in ('revenue_target', 'budget_total', 'marketing_spend', 'target_roi', 'timeline_months'):
                        if k in data and data.get(k) not in (None, ''):
                            csv_summary[k] = data.get(k)

                metrics = csv_summary if csv_summary else {'note': 'No numeric CSV metrics provided.'}
                performance = {'rating': 'N/A', 'notes': 'This is a strategic planning sequence rather than a performance score.'}
                recommendations = steps
                additional_data = {'plan_steps': steps, 'csv_summary': csv_summary, 'requested_by': forced}

                report = format_business_report('Best Way Strategic Planning', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
                # Return HTML if available, otherwise plain text
                return report.get('business_report_html', report.get('business_report', '\n'.join(steps)))

            def _positive(key):
                try:
                    val = data.get(key, None)
                    if val is None:
                        return False
                    return float(val) > 0
                except Exception:
                    return False

            if 'growth' in forced:
                # If CSV contains business-goal fields with positive values, prefer Business Goals
                if any(_positive(k) for k in ('revenue_target', 'revenue_target_total', 'budget_total', 'budget_total_sum', 'marketing_spend', 'marketing_spend_sum')):
                    # Build Business Goals report
                    rev = float(data.get('revenue_target') or data.get('revenue_target_total') or 0)
                    bud = float(data.get('budget_total') or data.get('budget_total_sum') or 0)
                    mkt = float(data.get('marketing_spend') or data.get('marketing_spend_sum') or 0)
                    try:
                        roi_v = float(data.get('target_roi') or 0)
                    except Exception:
                        roi_v = 0
                    try:
                        tl = int(float(data.get('timeline_months') or 12))
                    except Exception:
                        tl = 12

                    metrics = {
                        'revenue_target': rev,
                        'budget_total': bud,
                        'marketing_spend': mkt,
                        'target_roi': roi_v,
                        'timeline_months': tl
                    }
                    total_spend = (bud or 0) + (mkt or 0)
                    projected_net = (rev or 0) - total_spend
                    roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0
                    performance = {'rating': 'Good' if roi_achieved >= (roi_v or 0) else 'Needs Improvement', 'roi_achieved': roi_achieved}
                    recommendations = []
                    if roi_achieved < (roi_v or 0):
                        recommendations.append('Reduce budget or increase revenue initiatives to meet target ROI')
                    if mkt > 0 and (mkt / max(total_spend, 1)) > 0.5:
                        recommendations.append('Rebalance marketing spend to ensure efficient ROI')
                    if rev < total_spend:
                        recommendations.append('Reassess revenue assumptions; consider phased rollout to reduce upfront spend')
                    if not recommendations:
                        recommendations.append('Execute the plan and monitor monthly progress against KPIs')

                    additional_data = {'financials': {'Total Spend': total_spend, 'Projected Net': projected_net, 'ROI Achieved': f"{roi_achieved:.1f}%"}}
                    logger.info("Routing: Business Goals (forced 'growth' detected but business fields present)")
                    report = format_business_report('Business Goals Analysis', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
                    return report.get('business_report_html', report.get('business_report', 'Analysis completed but no report generated.'))

                # Otherwise attempt growth only if growth fields are positive
                if any(_positive(k) for k in ('market_size', 'market_share', 'investment_budget', 'competition_level')):
                    logger.info("Routing: Growth Strategy (forced by analysis type and positive market_* fields)")
                    result, status = task_registry.execute_task(service="strategic", subtask="growth_strategy", params=data)
                    if result.get('status') == 'success':
                        return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                    else:
                        return f"Error: {result.get('error', 'Analysis failed')}"
                else:
                    return "To analyze growth strategy, please provide Market Size, Market Share, Competition Level, and Investment Budget."

            if 'business' in forced or 'goals' in forced:
                # explicit Business Goals request: build and return the report deterministically
                rev = float(data.get('revenue_target') or data.get('revenue_target_total') or 0)
                bud = float(data.get('budget_total') or data.get('budget_total_sum') or 0)
                mkt = float(data.get('marketing_spend') or data.get('marketing_spend_sum') or 0)
                try:
                    roi_v = float(data.get('target_roi') or 0)
                except Exception:
                    roi_v = 0
                try:
                    tl = int(float(data.get('timeline_months') or 12))
                except Exception:
                    tl = 12

                metrics = {'revenue_target': rev, 'budget_total': bud, 'marketing_spend': mkt, 'target_roi': roi_v, 'timeline_months': tl}
                total_spend = (bud or 0) + (mkt or 0)
                projected_net = (rev or 0) - total_spend
                roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0
                performance = {'rating': 'Good' if roi_achieved >= (roi_v or 0) else 'Needs Improvement', 'roi_achieved': roi_achieved}
                recommendations = []
                if roi_achieved < (roi_v or 0):
                    recommendations.append('Reduce budget or increase revenue initiatives to meet target ROI')
                if mkt > 0 and (mkt / max(total_spend, 1)) > 0.5:
                    recommendations.append('Rebalance marketing spend to ensure efficient ROI')
                if rev < total_spend:
                    recommendations.append('Reassess revenue assumptions; consider phased rollout to reduce upfront spend')
                if not recommendations:
                    recommendations.append('Execute the plan and monitor monthly progress against KPIs')

                additional_data = {'financials': {'Total Spend': total_spend, 'Projected Net': projected_net, 'ROI Achieved': f"{roi_achieved:.1f}%"}}
                report = format_business_report('Business Goals Analysis', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
                return report.get('business_report_html', report.get('business_report', 'Analysis completed but no report generated.'))
            if 'sales' in forced or 'forecast' in forced:
                if any(k in data for k in ['historical_sales', 'current_sales', 'growth_rate', 'seasonal_factor']):
                    result, status = task_registry.execute_task(
                        service="strategic",
                        subtask="sales_forecasting",
                        params=data
                    )
                    if result.get('status') == 'success':
                        return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                    else:
                        return f"Error: {result.get('error', 'Analysis failed')}"
                else:
                    return "To forecast sales, provide Historical Sales, Current Sales, Growth Rate, and Seasonal Factor."
            if 'operational' in forced or 'excellence' in forced:
                if any(k in data for k in ['efficiency_score', 'process_time', 'quality_rating', 'customer_satisfaction']):
                    result, status = task_registry.execute_task(
                        service="strategic",
                        subtask="operational_excellence",
                        params=data
                    )
                    if result.get('status') == 'success':
                        return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                    else:
                        return f"Error: {result.get('error', 'Analysis failed')}"
                else:
                    return "To analyze operational excellence, provide Efficiency Score, Process Time, Quality Rating, and Customer Satisfaction."

        # Determine which analysis to run based on keywords
        prompt_lower = prompt.lower()

        # Prefer Business Goals when CSV-extracted business fields are present and positive,
        # and only treat growth as present when market_* fields are positive.
        business_keys = {'revenue_target', 'revenue_target_total', 'budget_total', 'budget_total_sum', 'marketing_spend', 'marketing_spend_sum', 'target_roi', 'timeline_months'}
        growth_keys = {'market_size', 'market_share', 'competition_level', 'investment_budget'}

        def _positive(key):
            try:
                val = data.get(key, None)
                if val is None:
                    return False
                return float(val) > 0
            except Exception:
                return False

        if any(_positive(k) for k in business_keys):
            rev = None
            bud = None
            mkt = 0
            roi_v = 0
            tl = 12

            if 'revenue_target' in data:
                rev = float(data.get('revenue_target') or 0)
            elif 'revenue_target_total' in data:
                rev = float(data.get('revenue_target_total') or 0)

            if 'budget_total' in data:
                bud = float(data.get('budget_total') or 0)
            elif 'budget_total_sum' in data:
                bud = float(data.get('budget_total_sum') or 0)

            if 'marketing_spend' in data:
                mkt = float(data.get('marketing_spend') or 0)
            elif 'marketing_spend_sum' in data:
                mkt = float(data.get('marketing_spend_sum') or 0)

            if 'target_roi' in data:
                try:
                    roi_v = float(data.get('target_roi') or 0)
                except Exception:
                    roi_v = 0

            if 'timeline_months' in data:
                try:
                    tl = int(float(data.get('timeline_months')))
                except Exception:
                    tl = 12

            metrics = {
                'revenue_target': rev or 0,
                'budget_total': bud or 0,
                'marketing_spend': mkt or 0,
                'target_roi': roi_v or 0,
                'timeline_months': tl
            }

            total_spend = (metrics.get('budget_total') or 0) + (metrics.get('marketing_spend') or 0)
            projected_net = (metrics.get('revenue_target') or 0) - total_spend
            roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0

            performance = {
                'rating': 'Good' if roi_achieved >= metrics.get('target_roi', 0) else 'Needs Improvement',
                'roi_achieved': roi_achieved
            }

            recommendations = []
            if roi_achieved < metrics.get('target_roi', 0):
                recommendations.append('Reduce budget or increase revenue initiatives to meet target ROI')
            if metrics.get('marketing_spend', 0) > 0 and (metrics.get('marketing_spend', 0) / max(total_spend, 1)) > 0.5:
                recommendations.append('Rebalance marketing spend to ensure efficient ROI')
            if metrics.get('revenue_target', 0) < total_spend:
                recommendations.append('Reassess revenue assumptions; consider phased rollout to reduce upfront spend')
            if not recommendations:
                recommendations.append('Execute the plan and monitor monthly progress against KPIs')

            additional_data = {
                'financials': {
                    'Total Spend': total_spend,
                    'Projected Net': projected_net,
                    'ROI Achieved': f"{roi_achieved:.1f}%"
                }
            }

            logger.info("Routing: Business Goals (data-driven detection)")
            report = format_business_report('Business Goals Analysis', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
            return report.get('business_report_html', report.get('business_report', 'Analysis completed but no report generated.'))

        # Import here to avoid circular imports
        from apps.agent_core.task_registry import task_registry
        
        # =====================================================
        # IMPORTANT: Check for ANALYSIS REQUEST keywords first
        # Use regex patterns that look for "analyze X" or "X analysis"
        # This prevents data mentions like "food cost: $14,000" from 
        # triggering the wrong analysis type
        # =====================================================
        
        # Helper function to detect analysis request type
        def is_requesting_analysis(analysis_type):
            """Check if user is requesting a specific analysis type (not just mentioning data)"""
            patterns = [
                rf'analyze\s+(?:my\s+)?{analysis_type}',
                rf'{analysis_type}\s+analysis',
                rf'calculate\s+(?:my\s+)?{analysis_type}',
                rf'check\s+(?:my\s+)?{analysis_type}',
                rf'show\s+(?:me\s+)?(?:my\s+)?{analysis_type}',
                rf'what\s+is\s+(?:my\s+)?{analysis_type}',
                rf'get\s+(?:my\s+)?{analysis_type}',
            ]
            return any(re.search(pattern, prompt_lower) for pattern in patterns)

        # Check for KPI Dashboard analysis requests first (most specific)
        if any(keyword in prompt_lower for keyword in ['comprehensive analysis', 'multi-metric analysis', 'industry benchmarking']):
            if 'total_sales' in data and 'labor_cost' in data and 'food_cost' in data and 'prime_cost' in data:
                result, status = task_registry.execute_task(
                    service="kpi_dashboard",
                    subtask="comprehensive_analysis",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To run comprehensive analysis, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Labor Cost (e.g., $15,000)
3. Food Cost (e.g., $14,000)
4. Prime Cost (e.g., $29,000)

**Optional:**
- Hours Worked (e.g., 800)
- Hourly Rate (e.g., $15)
- Previous Sales (e.g., $48,000)
- Target Margin (e.g., 70%)

Example: "Run comprehensive analysis. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Prime cost: $29,000."

Or upload a CSV file with columns: total_sales, labor_cost, food_cost, prime_cost"""

        elif any(keyword in prompt_lower for keyword in ['performance optimization', 'optimization strategies', 'goal setting']):
            if 'current_performance' in data and 'target_performance' in data and 'optimization_potential' in data and 'efficiency_score' in data:
                result, status = task_registry.execute_task(
                    service="kpi_dashboard",
                    subtask="performance_optimization",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To optimize performance, I need your actual data. Please provide:

**Required:**
1. Current Performance (e.g., 75%)
2. Target Performance (e.g., 90%)
3. Optimization Potential (e.g., 20%)
4. Efficiency Score (e.g., 80%)

**Optional:**
- Baseline Metrics (e.g., 70%)
- Improvement Rate (e.g., 10%)
- Goal Timeframe (e.g., 90 days)
- Progress Tracking (e.g., 8)

Example: "Optimize performance. Current performance: 75%. Target performance: 90%. Optimization potential: 20%. Efficiency score: 80%."

Or upload a CSV file with columns: current_performance, target_performance, optimization_potential, efficiency_score"""

        # Check for Strategic Planning analysis requests
        elif any(keyword in prompt_lower for keyword in ['sales forecasting', 'historical trends', 'growth projections', 'forecast', 'forecast my sales']):
            # Accept more prompt variants ('forecast', 'forecast my sales') and also accept CSV field-name variants
            has_historical = 'historical_sales' in data or 'historicalsales' in data
            has_current = 'current_sales' in data or 'currentsales' in data
            has_growth = 'growth_rate' in data or 'growthrate' in data
            has_seasonal = 'seasonal_factor' in data or 'seasonalfactor' in data
            if has_historical and has_current and has_growth and has_seasonal:
                result, status = task_registry.execute_task(
                    service="strategic",
                    subtask="sales_forecasting",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To forecast sales, I need your actual data. Please provide:

**Required:**
1. Historical Sales (e.g., $45,000)
2. Current Sales (e.g., $50,000)
3. Growth Rate (e.g., 5%)
4. Seasonal Factor (e.g., 1.2)

**Optional:**
- Forecast Period (e.g., 12 months)
- Trend Strength (e.g., 0.5)
- Market Growth (e.g., 5%)
- Confidence Level (e.g., 85%)

Example: "Forecast my sales. Historical sales: $45,000. Current sales: $50,000. Growth rate: 5%. Seasonal factor: 1.2."

Or upload a CSV file with columns: historical_sales, current_sales, growth_rate, seasonal_factor"""

        # Business Goals (CSV-friendly) - this will generate an HTML report directly
        elif any(keyword in prompt_lower for keyword in ['business goals', 'business goal', 'revenue target', 'business_goals']):
            # Try to extract business goals style fields from the prompt
            # Allow for suffixes like _total or _sum that frontend produces (e.g. revenue_target_total)
            rev_match = re.search(r'revenue[_ ]?target(?:[_\w]*)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
            budget_match = re.search(r'budget(?:[_\w]*)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
            marketing_match = re.search(r'marketing[_ ]?spend(?:[_\w]*)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
            roi_match = re.search(r'(?:target[_ ]?roi|average[_ ]?target[_ ]?roi|target roi|average_target_roi_percent)[:\s]*([0-9]+(?:\.[0-9]+)?)%?', prompt_lower)
            timeline_match = re.search(r'(?:timeline[_ ]?months|timeline|timeline_months)[:\s]*([0-9,]+)', prompt_lower)

            revenue = float(rev_match.group(1).replace(',', '')) if rev_match else (
                float(data.get('revenue_target', 0)) if 'revenue_target' in data else (
                    float(data.get('revenue_target_total', 0)) if 'revenue_target_total' in data else None
                )
            )
            budget = float(budget_match.group(1).replace(',', '')) if budget_match else (
                float(data.get('budget_total', 0)) if 'budget_total' in data else (
                    float(data.get('budget_total_sum', 0)) if 'budget_total_sum' in data else None
                )
            )
            marketing = float(marketing_match.group(1).replace(',', '')) if marketing_match else (
                float(data.get('marketing_spend', 0)) if 'marketing_spend' in data else (
                    float(data.get('marketing_spend_sum', 0)) if 'marketing_spend_sum' in data else 0
                )
            )
            roi = float(roi_match.group(1)) if roi_match else (
                float(data.get('target_roi', 0)) if 'target_roi' in data else (
                    float(data.get('average_target_roi_percent', 0)) if 'average_target_roi_percent' in data else 0
                )
            )
            timeline = int(timeline_match.group(1)) if timeline_match else (
                int(float(data.get('timeline_months'))) if 'timeline_months' in data else 12
            )

            if revenue is not None and budget is not None:
                total_spend = (budget or 0) + (marketing or 0)
                projected_net = (revenue or 0) - total_spend
                roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0

                metrics = {
                    'revenue_target': revenue,
                    'budget_total': budget,
                    'marketing_spend': marketing,
                    'target_roi': roi,
                    'timeline_months': timeline,
                    'projected_net': projected_net,
                    'total_spend': total_spend
                }

                performance = {
                    'rating': 'Good' if roi_achieved >= roi else 'Needs Improvement',
                    'roi_achieved': roi_achieved
                }

                recommendations = []
                if roi_achieved < roi:
                    recommendations.append('Reduce budget or increase revenue initiatives to meet target ROI')
                if marketing > 0 and (marketing / total_spend) > 0.5:
                    recommendations.append('Rebalance marketing spend to ensure efficient ROI')
                if revenue < total_spend:
                    recommendations.append('Reassess revenue assumptions; consider phased rollout to reduce upfront spend')
                if not recommendations:
                    recommendations.append('Execute the plan and monitor monthly progress against KPIs')

                additional_data = {
                    'financials': {
                        'Total Spend': total_spend,
                        'Projected Net': projected_net,
                        'ROI Achieved': f"{roi_achieved:.1f}%"
                    }
                }

                report = format_business_report('Business Goals Analysis', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
                return report.get('business_report_html', report.get('business_report', 'Analysis completed but no report generated.'))
            else:
                return """To analyze business goals, please provide: Revenue Target, Budget Total, Marketing Spend, Target ROI (optional)."""

        elif any(keyword in prompt_lower for keyword in ['growth strategy', 'market analysis', 'competitive positioning']):
            # If the CSV contains business-goals fields, prefer Business Goals analysis
            business_keys = {'revenue_target', 'revenue_target_total', 'budget_total', 'budget_total_sum', 'marketing_spend', 'marketing_spend_sum', 'target_roi', 'timeline_months'}
            if any(_positive(k) for k in business_keys):
                rev = float(data.get('revenue_target') or data.get('revenue_target_total') or 0)
                bud = float(data.get('budget_total') or data.get('budget_total_sum') or 0)
                mkt = float(data.get('marketing_spend') or data.get('marketing_spend_sum') or 0)
                try:
                    roi_v = float(data.get('target_roi') or 0)
                except Exception:
                    roi_v = 0
                try:
                    tl = int(float(data.get('timeline_months') or 12))
                except Exception:
                    tl = 12

                metrics = {'revenue_target': rev, 'budget_total': bud, 'marketing_spend': mkt, 'target_roi': roi_v, 'timeline_months': tl}
                total_spend = (bud or 0) + (mkt or 0)
                projected_net = (rev or 0) - total_spend
                roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0
                performance = {'rating': 'Good' if roi_achieved >= (roi_v or 0) else 'Needs Improvement', 'roi_achieved': roi_achieved}
                recommendations = []
                if roi_achieved < (roi_v or 0):
                    recommendations.append('Reduce budget or increase revenue initiatives to meet target ROI')
                if mkt > 0 and (mkt / max(total_spend, 1)) > 0.5:
                    recommendations.append('Rebalance marketing spend to ensure efficient ROI')
                if rev < total_spend:
                    recommendations.append('Reassess revenue assumptions; consider phased rollout to reduce upfront spend')
                if not recommendations:
                    recommendations.append('Execute the plan and monitor monthly progress against KPIs')

                additional_data = {'financials': {'Total Spend': total_spend, 'Projected Net': projected_net, 'ROI Achieved': f"{roi_achieved:.1f}%"}}
                report = format_business_report('Business Goals Analysis', metrics, performance, recommendations, benchmarks=None, additional_data=additional_data)
                return report.get('business_report_html', report.get('business_report', 'Analysis completed but no report generated.'))

            # Otherwise require positive growth fields
            if all(_positive(k) for k in ('market_size', 'market_share', 'competition_level', 'investment_budget')):
                result, status = task_registry.execute_task(
                    service="strategic",
                    subtask="growth_strategy",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze growth strategy, I need your actual data. Please provide:

**Required:**
1. Market Size (e.g., $5,000,000)
2. Market Share (e.g., 8%)
3. Competition Level (e.g., 65%)
4. Investment Budget (e.g., $100,000)

**Optional:**
- Growth Potential (e.g., 15%)
- Competitive Advantage (e.g., 7)
- Market Penetration (e.g., 5%)
- Target ROI (e.g., 20%)

Example: "Analyze growth strategy. Market size: $5,000,000. Market share: 8%. Competition level: 65%. Investment budget: $100,000."

Or upload a CSV file with columns: market_size, market_share, competition_level, investment_budget"""

        elif any(keyword in prompt_lower for keyword in ['operational excellence', 'process optimization', 'efficiency metrics']):
            if 'efficiency_score' in data and 'process_time' in data and 'quality_rating' in data and 'customer_satisfaction' in data:
                result, status = task_registry.execute_task(
                    service="strategic",
                    subtask="operational_excellence",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze operational excellence, I need your actual data. Please provide:

**Required:**
1. Efficiency Score (e.g., 80%)
2. Process Time (e.g., 25 minutes)
3. Quality Rating (e.g., 4.5)
4. Customer Satisfaction (e.g., 85%)

**Optional:**
- Cost Per Unit (e.g., $12)
- Waste Percentage (e.g., 5%)
- Productivity Score (e.g., 8)
- Industry Benchmark (e.g., 85%)

Example: "Analyze operational excellence. Efficiency score: 80%. Process time: 25 minutes. Quality rating: 4.5. Customer satisfaction: 85%."

Or upload a CSV file with columns: efficiency_score, process_time, quality_rating, customer_satisfaction"""

        # Create Recipe: generate ingredient suggestions, auto-costing, and nutrition analysis (HTML sections)
        elif any(keyword in prompt_lower for keyword in ['create a recipe', 'create recipe', 'recipe named']):
            # Basic extractions
            recipe_name = data.get('recipe_name')
            servings = data.get('servings')
            ingredient_cost = data.get('ingredient_cost')
            labor_cost = data.get('labor_cost')
            recipe_price = data.get('recipe_price')

            # Capture a simple ingredients line and prep/cook times if present
            import urllib.parse
            decoded_prompt_full = urllib.parse.unquote(prompt)
            ing_line = None
            m = re.search(r'ingredients?[:\s]*(.*)', decoded_prompt_full, re.IGNORECASE)
            if m:
                ing_line = m.group(1).strip()
                stop = re.search(r'\.(?:\s|$)', ing_line)
                if stop:
                    ing_line = ing_line[:stop.start()] if stop.start() > 0 else ing_line
            # Parse prep_time and cook_time locally
            prep_val = None
            cook_val = None
            pm = re.search(r'(?:prep[\s_]*time)[:=\s]*([0-9]+(?:\.[0-9]+)?)', decoded_prompt_full, re.IGNORECASE)
            if pm:
                try:
                    prep_val = float(pm.group(1))
                except Exception:
                    prep_val = None
            cm = re.search(r'(?:cook[\s_]*time)[:=\s]*([0-9]+(?:\.[0-9]+)?)', decoded_prompt_full, re.IGNORECASE)
            if cm:
                try:
                    cook_val = float(cm.group(1))
                except Exception:
                    cook_val = None

            # Compute auto-costing if possible
            costing_text = None
            try:
                if servings and (ingredient_cost or 0) + (labor_cost or 0) > 0:
                    total_cost = float((ingredient_cost or 0)) + float((labor_cost or 0))
                    cps = total_cost / float(servings)
                    if recipe_price and float(recipe_price) > 0:
                        margin = ((float(recipe_price) - cps) / float(recipe_price)) * 100
                        costing_text = (
                            f"Auto-costing: Total cost ${total_cost:.2f}, cost per serving ${cps:.2f}. "
                            f"At price ${float(recipe_price):.2f}, estimated margin {margin:.1f}%"
                        )
                    else:
                        costing_text = (
                            f"Auto-costing: Total cost ${total_cost:.2f}, cost per serving ${cps:.2f}. "
                            f"Provide recipe_price to estimate margin."
                        )
            except Exception:
                costing_text = None

            # Build AI prompts for ingredient suggestions/steps and nutrition separately
            suggestions_text = None
            nutrition_text = None
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    client = OpenAI(api_key=api_key)
                    # Build common context
                    context_lines = []
                    if recipe_name:
                        context_lines.append(f"Recipe Name: {recipe_name}")
                    if servings:
                        context_lines.append(f"Servings: {int(float(servings))}")
                    if ing_line:
                        context_lines.append(f"Ingredients: {ing_line}")
                    if prep_val is not None:
                        context_lines.append(f"Prep Time: {int(prep_val)} minutes")
                    if cook_val is not None:
                        context_lines.append(f"Cook Time: {int(cook_val)} minutes")

                    ai_content = "\n".join(context_lines)
                    # 1) Ingredient suggestions + steps
                    sugg_system = (
                        "Provide clear, natural English. No markdown or special formatting. "
                        "Write like a helpful chef. Include: 1) Ingredient suggestions with rough quantities, 2) 6-8 concise cooking steps."
                    )
                    sugg_user = (
                        "Based on the context, propose complementary ingredient suggestions (with rough quantities and common units) "
                        "and provide 6-8 concise steps to prepare the dish."
                    )
                    resp1 = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": sugg_system},
                            {"role": "user", "content": f"{sugg_user}\n\n{ai_content}"},
                        ],
                        temperature=0.7,
                        max_tokens=900,
                    )
                    suggestions_text = resp1.choices[0].message.content

                    # 2) Nutrition analysis per serving
                    nutr_system = (
                        "Provide clear, natural English. No markdown or special formatting. "
                        "Estimate per-serving nutrition with brief rationale, including calories, protein (g), carbs (g), and fat (g)."
                    )
                    nutr_user = (
                        "Based on the context, estimate per-serving nutrition (calories, protein grams, carbs grams, fat grams). "
                        "Provide a short rationale for key drivers of the estimate."
                    )
                    resp2 = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": nutr_system},
                            {"role": "user", "content": f"{nutr_user}\n\n{ai_content}"},
                        ],
                        temperature=0.5,
                        max_tokens=600,
                    )
                    nutrition_text = resp2.choices[0].message.content
                else:
                    suggestions_text = (
                        "AI ingredient suggestions are unavailable because the AI key is not configured. "
                        "Please set OPENAI_API_KEY to enable this feature."
                    )
                    nutrition_text = (
                        "AI nutrition analysis is unavailable because the AI key is not configured. "
                        "Please set OPENAI_API_KEY to enable this feature."
                    )
            except Exception as e:
                suggestions_text = f"Ingredient suggestions unavailable: {str(e)}"
                nutrition_text = f"Nutrition analysis unavailable: {str(e)}"

            # Build minimal HTML with three sections
            def _p(s):
                return (s or '').replace('\n\n', '\n').replace('\n', '<br>')

            html_parts = []
            html_parts.append('<div style="display:flex;flex-direction:column;gap:12px;color: var(--text-primary, #111827); font-size: 14px; line-height: 1.6;">')
            # Header
            title_bits = []
            if recipe_name:
                title_bits.append(f"<strong>{recipe_name}</strong>")
            if servings:
                try:
                    title_bits.append(f"Servings: {int(float(servings))}")
                except Exception:
                    pass
            if prep_val is not None:
                title_bits.append(f"Prep: {int(prep_val)} min")
            if cook_val is not None:
                title_bits.append(f"Cook: {int(cook_val)} min")
            if title_bits:
                html_parts.append('<div style="font-size:14px;color: var(--text-secondary, #374151);">' + ' • '.join(title_bits) + '</div>')

            # Ingredient Suggestions
            html_parts.append('<div style="background: rgba(59,130,246,0.08); padding:12px; border-radius:8px; border:1px solid rgba(59,130,246,0.25);">')
            html_parts.append('<div style="font-weight:600; color: var(--accent-primary, #1d4ed8); margin-bottom:6px;">Ingredient Suggestions</div>')
            html_parts.append(f'<div style="font-size:14px; line-height:1.6; color: var(--text-primary, #111827);">{_p(suggestions_text)}</div>')
            html_parts.append('</div>')

            # Auto-Costing
            html_parts.append('<div style="background: rgba(16,185,129,0.08); padding:12px; border-radius:8px; border:1px solid rgba(16,185,129,0.25);">')
            html_parts.append('<div style="font-weight:600; color: #059669; margin-bottom:6px;">Auto-Costing</div>')
            auto_cost_text = costing_text or 'No costing available. Provide ingredient_cost, labor_cost, and servings.'
            html_parts.append(f'<div style="font-size:14px; line-height:1.6; color: var(--text-primary, #111827);">{_p(auto_cost_text)}</div>')
            html_parts.append('</div>')

            # Nutrition Analysis
            html_parts.append('<div style="background: rgba(139,92,246,0.08); padding:12px; border-radius:8px; border:1px solid rgba(139,92,246,0.25);">')
            html_parts.append('<div style="font-weight:600; color:#6d28d9; margin-bottom:6px;">Nutrition Analysis</div>')
            html_parts.append(f'<div style="font-size:14px; line-height:1.6; color: var(--text-primary, #111827);">{_p(nutrition_text)}</div>')
            html_parts.append('</div>')

            html_parts.append('</div>')
            return ''.join(html_parts)

        # Check for Recipe Management costing requests (intent-specific)
        elif any(keyword in prompt_lower for keyword in ['recipe costing', 'analyze recipe costs', 'portion cost']):
            # Route to recipe costing if key metrics are present or keywords indicate costing
            if 'ingredient_cost' in data and 'portion_cost' in data and 'recipe_price' in data:
                result, status = task_registry.execute_task(
                    service="recipe",
                    subtask="costing",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze recipe costing, please provide:

**Required:**
1. Ingredient Cost (e.g., $5.50)
2. Portion Cost (e.g., $2.25)
3. Recipe Price (e.g., $15)

**Optional:**
- Servings (e.g., 4)
- Labor Cost (e.g., $3)
- Overhead Cost (e.g., $1.50)

Example: "Analyze recipe costs of: recipe_name \"Grilled Salmon\", ingredient_cost 5.80, portion_cost 2.30, recipe_price 13.50, servings 2, labor_cost 3.50."

Or upload a CSV file with columns: recipe_name, ingredient_cost, portion_cost, recipe_price, servings, labor_cost"""

        elif any(keyword in prompt_lower for keyword in ['ingredient optimization', 'supplier cost', 'waste reduction']):
            if 'current_cost' in data and 'supplier_cost' in data and 'waste_percentage' in data and 'quality_score' in data:
                result, status = task_registry.execute_task(
                    service="recipe",
                    subtask="ingredient_optimization",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To optimize ingredients, I need your actual data. Please provide:

**Required:**
1. Current Cost (e.g., $5.50)
2. Supplier Cost (e.g., $4.50)
3. Waste Percentage (e.g., 8%)
4. Quality Score (e.g., 85%)

**Optional:**
- Volume Discount (e.g., 10%)
- Storage Cost (e.g., $0.50)
- Shelf Life Days (e.g., 7)

Example: "Optimize ingredients. Current cost: $5.50. Supplier cost: $4.50. Waste percentage: 8%. Quality score: 85%."

Or upload a CSV file with columns: current_cost, supplier_cost, waste_percentage, quality_score"""

        elif any(keyword in prompt_lower for keyword in ['recipe scaling', 'batch size', 'yield calculation', 'scale recipe', 'scale "', 'scale recipes']):
            # If we have current/target batch, ensure defaults for missing metrics
            if 'current_batch' in data and 'target_batch' in data:
                if 'yield_percentage' not in data or not data.get('yield_percentage'):
                    data['yield_percentage'] = 90.0
                if 'consistency_score' not in data or not data.get('consistency_score'):
                    data['consistency_score'] = 8.0
            if 'current_batch' in data and 'target_batch' in data and 'yield_percentage' in data and 'consistency_score' in data:
                result, status = task_registry.execute_task(
                    service="recipe",
                    subtask="scaling",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To scale recipes, please provide:

**Required:**
1. Current Batch (e.g., 10 servings)
2. Target Batch (e.g., 50 servings)
3. Yield Percentage (e.g., 95%)
4. Consistency Score (e.g., 90%)

**Optional:**
- Scale Factor (e.g., 5)
- Ingredient Adjustment (e.g., 1.1)
- Equipment Capacity (e.g., 100)

Example: "Scale \"Classic Tomato Soup\" which serves 6 to 48 servings. Provide ingredient quantities, converted units, and suggested batch yields."

Or upload a CSV file with columns: current_batch, target_batch, yield_percentage, consistency_score"""

        # Create Recipe: generate ingredient suggestions, auto-costing, and nutrition analysis (plain text)
        elif any(keyword in prompt_lower for keyword in ['create a recipe', 'create recipe', 'recipe named']):
            # Basic extractions
            recipe_name = data.get('recipe_name')
            servings = data.get('servings')
            ingredient_cost = data.get('ingredient_cost')
            labor_cost = data.get('labor_cost')
            recipe_price = data.get('recipe_price')

            # Capture a simple ingredients line if present
            import urllib.parse
            decoded_prompt_full = urllib.parse.unquote(prompt)
            ing_line = None
            m = re.search(r'ingredients?[:\s]*(.*)', decoded_prompt_full, re.IGNORECASE)
            if m:
                ing_line = m.group(1).strip()
                stop = re.search(r'\.(?:\s|$)', ing_line)
                if stop:
                    ing_line = ing_line[:stop.start()] if stop.start() > 0 else ing_line

            # Compute auto-costing if possible
            costing_text = None
            try:
                if servings and (ingredient_cost or 0) + (labor_cost or 0) > 0:
                    total_cost = float((ingredient_cost or 0)) + float((labor_cost or 0))
                    cps = total_cost / float(servings)
                    if recipe_price and float(recipe_price) > 0:
                        margin = ((float(recipe_price) - cps) / float(recipe_price)) * 100
                        costing_text = (
                            f"Auto-costing: Total cost ${total_cost:.2f}, cost per serving ${cps:.2f}. "
                            f"At price ${float(recipe_price):.2f}, estimated margin {margin:.1f}%"
                        )
                    else:
                        costing_text = (
                            f"Auto-costing: Total cost ${total_cost:.2f}, cost per serving ${cps:.2f}. "
                            f"Provide recipe_price to estimate margin."
                        )
            except Exception:
                costing_text = None

            # Build AI prompt for ingredient suggestions and nutrition
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    client = OpenAI(api_key=api_key)
                    user_prompt = (
                        "You are an expert chef and nutritionist. Based on the following, suggest ingredients to complete a balanced recipe, "
                        "provide a brief step-by-step, and estimate nutrition per serving (calories, protein, carbs, fat)."
                    )
                    context_lines = []
                    if recipe_name:
                        context_lines.append(f"Recipe Name: {recipe_name}")
                    if servings:
                        context_lines.append(f"Servings: {int(float(servings))}")
                    if ing_line:
                        context_lines.append(f"Ingredients: {ing_line}")
                    if data.get('prep_time'):
                        context_lines.append(f"Prep Time: {int(float(data.get('prep_time')))} minutes")
                    if data.get('cook_time'):
                        context_lines.append(f"Cook Time: {int(float(data.get('cook_time')))} minutes")

                    ai_content = "\n".join(context_lines)

                    system_msg = (
                        "Provide clear, natural English. No markdown or special formatting. "
                        "Write like a helpful chef. Include: 1) Ingredient suggestions with rough quantities, "
                        "2) 6-8 concise steps, 3) Per-serving nutrition estimates with brief rationale."
                    )

                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": f"{user_prompt}\n\n{ai_content}"},
                        ],
                        temperature=0.7,
                        max_tokens=1200,
                    )
                    ai_text = response.choices[0].message.content
                else:
                    ai_text = (
                        "Ingredient suggestions and nutrition analysis are unavailable because the AI key is not configured. "
                        "Please set OPENAI_API_KEY to enable this feature."
                    )
            except Exception as e:
                ai_text = f"Ingredient suggestions and nutrition analysis unavailable: {str(e)}"

            combined = []
            if recipe_name:
                combined.append(f"Recipe: {recipe_name}")
            if servings:
                combined.append(f"Servings: {int(float(servings))}")
            if costing_text:
                combined.append(costing_text)
            combined.append(ai_text)
            return "\n\n".join(combined)

        # Check for Menu Engineering analysis requests
        elif any(keyword in prompt_lower for keyword in ['product mix', 'menu analysis', 'item performance', 'menu engineering']):
            if 'total_sales' in data and 'item_sales' in data and 'item_cost' in data and 'item_profit' in data:
                result, status = task_registry.execute_task(
                    service="menu",
                    subtask="product_mix",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze product mix, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Item Sales (e.g., $5,000)
3. Item Cost (e.g., $1,500)
4. Item Profit (e.g., $3,500)

**Or upload a CSV file with columns:**
- product_name (Menu item name)
- quantity_sold (Units sold)
- unit_price (Selling price)
- cost (Cost per unit)

Example CSV format:
product_name,quantity_sold,unit_price,cost
Margherita Pizza,94,21,6
Pepperoni Pizza,125,22,5"""

        elif any(keyword in prompt_lower for keyword in ['menu pricing', 'menu price optimization']):
            if 'item_price' in data and 'item_cost' in data and 'competitor_price' in data:
                result, status = task_registry.execute_task(
                    service="menu",
                    subtask="pricing",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze menu pricing, I need your actual data. Please provide:

**Required:**
1. Item Price (e.g., $18)
2. Item Cost (e.g., $5.50)
3. Competitor Price (e.g., $16)

**Optional:**
- Target Food Cost % (e.g., 32%)

Example: "Analyze menu pricing. Item price: $18. Item cost: $5.50. Competitor price: $16."

Or upload a CSV file with columns: item_price, item_cost, competitor_price"""

        elif any(keyword in prompt_lower for keyword in ['menu design', 'design analysis', 'visual hierarchy']):
            if 'menu_items' in data and 'high_profit_items' in data and 'sales_distribution' in data and 'visual_hierarchy' in data:
                result, status = task_registry.execute_task(
                    service="menu",
                    subtask="design",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze menu design, I need your actual data. Please provide:

**Required:**
1. Menu Items (e.g., 25)
2. High Profit Items (e.g., 8)
3. Sales Distribution (e.g., "40% appetizers, 60% entrees")
4. Visual Hierarchy (e.g., "top-right placement")

**Or upload a CSV file** with your menu items for product mix analysis first.

The system will analyze your menu and provide:
- Golden Triangle placement recommendations
- Visual hierarchy optimization
- Category sequencing suggestions"""

        # Check for Beverage Management analysis requests
        elif any(keyword in prompt_lower for keyword in ['liquor cost', 'liquor analysis', 'liquor variance']):
            if 'expected_oz' in data and 'actual_oz' in data and 'liquor_cost' in data and 'total_sales' in data:
                result, status = task_registry.execute_task(
                    service="beverage",
                    subtask="liquor_cost",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your liquor cost, I need your actual data. Please provide:

**Required:**
1. Expected Ounces (e.g., 500 oz)
2. Actual Ounces (e.g., 480 oz)
3. Liquor Cost (e.g., $3,500)
4. Total Sales (e.g., $15,000)

**Optional:**
- Bottle Cost (e.g., $25)
- Bottle Size (e.g., 25 oz)
- Target Cost Percentage (e.g., 20%)

Example: "Analyze my liquor cost. Expected oz: 500. Actual oz: 480. Liquor cost: $3,500. Total sales: $15,000. Bottle cost: $25."

Or upload a CSV file with columns: expected_oz, actual_oz, liquor_cost, total_sales"""

        elif any(keyword in prompt_lower for keyword in ['bar inventory', 'inventory management', 'stock level']):
            if 'current_stock' in data and 'reorder_point' in data and 'monthly_usage' in data and 'inventory_value' in data:
                result, status = task_registry.execute_task(
                    service="beverage",
                    subtask="inventory",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your bar inventory, I need your actual data. Please provide:

**Required:**
1. Current Stock (e.g., 150 units)
2. Reorder Point (e.g., 30 units)
3. Monthly Usage (e.g., 100 units)
4. Inventory Value (e.g., $5,000)

**Optional:**
- Lead Time Days (e.g., 7 days)
- Safety Stock (e.g., 10 units)
- Item Cost (e.g., $25)
- Target Turnover (e.g., 12)

Example: "Analyze bar inventory. Current stock: 150. Reorder point: 30. Monthly usage: 100. Inventory value: $5,000. Lead time: 7 days."

Or upload a CSV file with columns: current_stock, reorder_point, monthly_usage, inventory_value"""

        elif any(keyword in prompt_lower for keyword in ['beverage pricing', 'drink pricing', 'pricing analysis']):
            if 'drink_price' in data and 'cost_per_drink' in data and 'sales_volume' in data and 'competitor_price' in data:
                result, status = task_registry.execute_task(
                    service="beverage",
                    subtask="pricing",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your beverage pricing, I need your actual data. Please provide:

**Required:**
1. Drink Price (e.g., $12)
2. Cost Per Drink (e.g., $3)
3. Sales Volume (e.g., 500 units)
4. Competitor Price (e.g., $11)

**Optional:**
- Target Margin (e.g., 75%)
- Market Position (e.g., premium, standard, value)
- Elasticity Factor (e.g., 1.5)

Example: "Analyze beverage pricing. Drink price: $12. Cost per drink: $3. Sales volume: 500. Competitor price: $11. Target margin: 75%."

Or upload a CSV file with columns: drink_price, cost_per_drink, sales_volume, competitor_price"""

        # Check for HR analysis requests
        elif any(keyword in prompt_lower for keyword in ['staff retention', 'retention analysis', 'turnover rate', 'turnover analysis']):
            if 'turnover_rate' in data:
                result, status = task_registry.execute_task(
                    service="hr",
                    subtask="staff_retention",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze staff retention, I need your actual data. Please provide:

**Required:**
1. Turnover Rate (e.g., 45%)

**Optional:**
- Industry Average (e.g., 70%)

Example: "Analyze staff retention. Turnover rate: 45%. Industry average: 70%."

Or upload a CSV file with columns: turnover_rate, industry_average"""

        elif any(keyword in prompt_lower for keyword in ['labor scheduling', 'scheduling optimization', 'staff scheduling', 'shift optimization']):
            if 'total_sales' in data and ('labor_hours' in data or 'hours_worked' in data) and 'hourly_rate' in data:
                result, status = task_registry.execute_task(
                    service="hr",
                    subtask="labor_scheduling",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To optimize labor scheduling, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Labor Hours (e.g., 800 hours)
3. Hourly Rate (e.g., $15)

**Optional:**
- Peak Hours (e.g., 200 hours)

Example: "Optimize labor scheduling. Total sales: $50,000. Labor hours: 800. Hourly rate: $15. Peak hours: 200."

Or upload a CSV file with columns: total_sales, labor_hours, hourly_rate, peak_hours"""

        elif any(keyword in prompt_lower for keyword in [
            'performance management',
            'staff performance',
            'performance analysis',
            'employee performance',
            'training program',
            'training programs',
            'onboarding',
            'skill development',
            'performance tracking'
        ]):
            # For performance management, we need at least one performance metric
            if any(key in data for key in ['customer_satisfaction', 'sales_performance', 'efficiency_score', 'attendance_rate']):
                result, status = task_registry.execute_task(
                    service="hr",
                    subtask="performance_management",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze staff performance, I need your actual data. Please provide at least one metric:

**Required (at least one):**
1. Customer Satisfaction (e.g., 85%)
2. Sales Performance (e.g., 95%)
3. Efficiency Score (e.g., 80%)
4. Attendance Rate (e.g., 92%)

**Optional:**
- Target Satisfaction (e.g., 90%)
- Target Sales (e.g., 100%)
- Target Efficiency (e.g., 85%)
- Target Attendance (e.g., 98%)

Example: "Analyze staff performance. Customer satisfaction: 85%. Sales performance: 95%. Efficiency score: 80%. Attendance rate: 92%."

Or upload a CSV file with columns: customer_satisfaction, sales_performance, efficiency_score, attendance_rate"""

        # =====================================================
        # CORE KPI ANALYSIS - Use is_requesting_analysis() to detect intent
        # Order matters: more specific analyses first
        # =====================================================
        
        # PRIME COST ANALYSIS - Check first (contains both labor and food, so must come before individual checks)
        elif is_requesting_analysis('prime cost') or is_requesting_analysis('prime') or 'prime cost' in prompt_lower.split('analyze')[-1] if 'analyze' in prompt_lower else False:
            logger.info(f"Prime cost analysis requested")
            if 'total_sales' in data and 'labor_cost' in data and 'food_cost' in data:
                result, status = task_registry.execute_task(
                    service="kpi",
                    subtask="prime_cost",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your prime cost, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Labor Cost (e.g., $15,000)  
3. Food Cost (e.g., $14,000)

**Optional:**
- Covers served (e.g., 2,000)

Example: "Analyze my prime cost. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Covers served: 2,000."

Or upload a CSV file with columns: date, sales, labor_cost, food_cost"""

        # SALES PERFORMANCE ANALYSIS - Check second (requires all 4 core metrics)
        elif is_requesting_analysis('sales performance') or is_requesting_analysis('sales') or is_requesting_analysis('revenue') or is_requesting_analysis('growth'):
            logger.info(f"Sales performance analysis requested")
            if 'total_sales' in data and 'labor_cost' in data and 'food_cost' in data and 'hours_worked' in data:
                result, status = task_registry.execute_task(
                    service="kpi",
                    subtask="sales_performance",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your sales performance, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Labor Cost (e.g., $15,000)
3. Food Cost (e.g., $14,000)
4. Hours Worked (e.g., 800 hours)

**Optional:**
- Previous Sales (e.g., $48,000)
- Covers served (e.g., 2,000)
- Average Check (e.g., $25)

Example: "Analyze my sales performance. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Hours worked: 800. Previous sales: $48,000. Covers served: 2,000. Average check: $25."

Or upload a CSV file with columns: date, sales, labor_cost, food_cost, labor_hours"""

        # LABOR COST ANALYSIS - Check for explicit labor cost request
        elif is_requesting_analysis('labor cost') or is_requesting_analysis('labor'):
            logger.info(f"Labor cost analysis requested")
            if 'total_sales' in data and 'labor_cost' in data and 'hours_worked' in data:
                result, status = task_registry.execute_task(
                    service="kpi",
                    subtask="labor_cost",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your labor cost, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Labor Cost (e.g., $15,000)
3. Hours Worked (e.g., 800 hours)

**Optional:**
- Overtime Hours (e.g., 40)
- Covers served (e.g., 2,000)

Example: "Analyze my labor cost. Total sales: $50,000. Labor cost: $15,000. Hours worked: 800. Overtime hours: 40. Covers served: 2,000."

Or upload a CSV file with columns: date, sales, labor_cost, labor_hours"""

        # FOOD COST ANALYSIS - Check for explicit food cost request
        elif is_requesting_analysis('food cost') or is_requesting_analysis('food') or is_requesting_analysis('cogs'):
            logger.info(f"Food cost analysis requested")
            if 'total_sales' in data and 'food_cost' in data:
                result, status = task_registry.execute_task(
                    service="kpi",
                    subtask="food_cost",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return """To analyze your food cost, I need your actual data. Please provide:

**Required:**
1. Total Sales (e.g., $50,000)
2. Food Cost (e.g., $14,000)

**Optional:**
- Waste Cost (e.g., $800)
- Covers served (e.g., 2,000)
- Beginning Inventory (e.g., $5,000)
- Ending Inventory (e.g., $4,500)

Example: "Analyze my food cost. Total sales: $50,000. Food cost: $14,000. Waste cost: $800. Covers served: 2,000. Beginning inventory: $5,000. Ending inventory: $4,500."

Or upload a CSV file with columns: date, sales, food_cost"""

        # Check for simple labor cost calculation with hourly rate - use task registry for proper HTML output
        elif any(keyword in prompt_lower for keyword in ['labor hours', 'hourly rate']):
            if 'total_sales' in data and 'hours_worked' in data:
                # Extract hourly rate from prompt or use default
                hourly_rate_match = re.search(r'(?:hourly\s+rate|rate)[:\s]*\$?([0-9.]+)', prompt, re.IGNORECASE)
                hourly_rate = float(hourly_rate_match.group(1)) if hourly_rate_match else 15.0
                
                # Calculate labor cost from hourly rate if not provided
                if 'labor_cost' not in data:
                    data['labor_cost'] = data['hours_worked'] * hourly_rate
                
                # Use task registry for HTML output
                result, status = task_registry.execute_task(
                    service="kpi",
                    subtask="labor_cost",
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"

        # Check for KPI summary - use sales_performance task for proper HTML output
        elif 'total_sales' in data and 'labor_cost' in data and 'food_cost' in data and 'hours_worked' in data:
            result, status = task_registry.execute_task(
                service="kpi",
                subtask="sales_performance",
                params=data
            )
            if result.get('status') == 'success':
                return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
            else:
                return f"Error: {result.get('error', 'Analysis failed')}"


        # Check for inventory variance
        elif any(keyword in prompt_lower for keyword in ['inventory', 'variance', 'expected', 'actual']):
            expected_match = re.search(r'(?:expected|forecast)[:\s]*([0-9.]+)', prompt, re.IGNORECASE)
            actual_match = re.search(r'(?:actual|used)[:\s]*([0-9.]+)', prompt, re.IGNORECASE)

            if expected_match and actual_match:
                result = calculate_inventory_variance(
                    expected_usage=float(expected_match.group(1)),
                    actual_usage=float(actual_match.group(1))
                )
                if result.get('status') == 'success':
                    # Use HTML version if available, fall back to text
                    return result.get('business_report_html', result.get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('message', 'Unknown error')}"

        return None  # No analysis detected

    except Exception as e:
        return f"Error processing KPI analysis: {str(e)}"


def handle_conversational_ai(prompt: str) -> str:
    """
    Route natural language queries to Conversational AI for menu/business analysis.

    This uses the Conversational AI endpoint which:
    - Classifies user intent (highest_selling, most_profitable, stars, dogs, etc.)
    - Calls appropriate business logic (menu engineering, pricing, design)
    - Returns conversational responses with insights and suggestions

    Args:
        prompt: User's natural language question

    Returns:
        Conversational response string, or None if not a conversational AI query
    """
    try:
        from apps.agent_core.task_registry import task_registry

        # Try Conversational AI endpoint
        result, status_code = task_registry.execute_task(
            service="conversational",
            subtask="ai",
            params={"query": prompt, "session_id": "chat_assistant"},
            file_bytes=None
        )

        if status_code == 200 and result.get("status") == "success":
            data = result.get("data", {})

            # Check for business_report_html first (from menu_questions)
            # It might be in data directly or in raw_data
            business_report_html = data.get("business_report_html") or data.get("raw_data", {}).get("business_report_html")
            if business_report_html:
                return business_report_html

            answer = data.get("answer", "")

            # Check if this was a "help" response (means query wasn't recognized)
            # If so, return None to fall through to GPT-4
            if answer.startswith("What I Can Help You With:") or answer.startswith("I'm not sure I understood that"):
                return None  # Fall through to GPT-4 for general questions

            # Format the conversational response
            insights = data.get("insights", [])
            suggestions = data.get("suggestions", [])

            # Build response with insights and suggestions
            response_parts = [answer]

            if insights:
                response_parts.append("\nInsights:")
                for insight in insights:
                    response_parts.append(f"- {insight}")

            if suggestions:
                response_parts.append("\nYou can also ask:")
                for suggestion in suggestions[:3]:  # Limit to 3 suggestions
                    response_parts.append(f"- {suggestion}")

            return "\n".join(response_parts)

        return None  # Not a conversational AI query

    except Exception as e:
        # If conversational AI fails, return None to fall through to other handlers
        return None


def handle_beverage_analysis(prompt: str) -> str:
    """Handle Beverage Management analysis requests via task registry."""
    import re
    try:
        from apps.agent_core.task_registry import task_registry

        prompt_lower = prompt.lower()
        data = {}

        # Extract liquor cost metrics
        expected_oz_match = re.search(r'expected\s+(?:oz|ounces?)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if expected_oz_match:
            data['expected_oz'] = float(expected_oz_match.group(1).replace(',', ''))

        actual_oz_match = re.search(r'actual\s+(?:oz|ounces?)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if actual_oz_match:
            data['actual_oz'] = float(actual_oz_match.group(1).replace(',', ''))

        liquor_cost_match = re.search(r'liquor\s+cost[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if liquor_cost_match:
            data['liquor_cost'] = float(liquor_cost_match.group(1).replace(',', ''))

        total_sales_match = re.search(r'total\s+sales[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if total_sales_match:
            data['total_sales'] = float(total_sales_match.group(1).replace(',', ''))

        waste_cost_match = re.search(r'waste\s+cost[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if waste_cost_match:
            data['waste_cost'] = float(waste_cost_match.group(1).replace(',', ''))

        covers_match = re.search(r'covers(?:\s+served)?[:\s]*([0-9,]+)', prompt_lower)
        if covers_match:
            data['covers'] = int(covers_match.group(1).replace(',', ''))

        bottle_cost_match = re.search(r'bottle\s+cost[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if bottle_cost_match:
            data['bottle_cost'] = float(bottle_cost_match.group(1).replace(',', ''))

        bottle_size_match = re.search(r'bottle\s+size[:\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:oz|ounces?)', prompt_lower)
        if bottle_size_match:
            data['bottle_size_oz'] = float(bottle_size_match.group(1).replace(',', ''))

        target_pct_match = re.search(r'target\s+cost\s+percentage[:\s]*([0-9,]+(?:\.[0-9]+)?)', prompt_lower)
        if target_pct_match:
            data['target_cost_percentage'] = float(target_pct_match.group(1).replace(',', ''))

        # Decide which beverage subtask to run
        def run_task(subtask: str, required_keys: list, help_text: str):
            if all(k in data for k in required_keys):
                result, status = task_registry.execute_task(
                    service="beverage",
                    subtask=subtask,
                    params=data
                )
                if result.get('status') == 'success':
                    return result.get('data', {}).get('business_report_html', result.get('data', {}).get('business_report', 'Analysis completed but no report generated.'))
                else:
                    return f"Error: {result.get('error', 'Analysis failed')}"
            else:
                return help_text

        # Liquor Cost Analysis
        if any(keyword in prompt_lower for keyword in ['liquor cost', 'beverage cost', 'pour cost', 'variance']):
            return run_task(
                'liquor_cost',
                ['liquor_cost', 'total_sales'],
                "To analyze liquor cost, please provide: Total Sales and Liquor Cost. Optional: Waste Cost, Covers, Expected Oz, Actual Oz, Bottle Cost, Bottle Size, Target Cost Percentage."
            )

        # Bar Inventory Analysis
        if any(keyword in prompt_lower for keyword in ['inventory', 'stock level', 'reorder', 'turnover']):
            return run_task(
                'inventory',
                ['current_stock', 'reorder_point', 'monthly_usage', 'inventory_value'],
                "To analyze bar inventory, provide: Current Stock, Reorder Point, Monthly Usage, Inventory Value. Optional: Lead Time Days, Safety Stock, Item Cost, Target Turnover."
            )

        # Beverage Pricing Analysis
        if any(keyword in prompt_lower for keyword in ['pricing', 'price', 'margin', 'profit']):
            return run_task(
                'pricing',
                ['drink_price', 'cost_per_drink', 'sales_volume', 'competitor_price'],
                "To analyze beverage pricing, provide: Drink Price, Cost per Drink, Sales Volume, Competitor Price. Optional: Target Margin, Market Position, Elasticity Factor."
            )

        return None
    except Exception:
        return None


def chat_with_gpt(
    prompt: str,
    context: str | None = None,
    history: list[dict] | None = None,
    *,
    max_history_messages: int = 20,
) -> str:
    """Chat with GPT-4 using the OpenAI API, with KPI and Beverage analysis integration."""
    if not prompt or not prompt.strip():
        return "Error: Please provide a message."

    def _coerce_history_messages(raw_history: list[dict] | None) -> list[dict]:
        if not raw_history:
            return []
        safe: list[dict] = []
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            safe.append({"role": role, "content": content.strip()})
        if max_history_messages and len(safe) > max_history_messages:
            safe = safe[-max_history_messages:]
        return safe

    def _normalize_chat_text(text: str) -> str:
        # Normalize for lightweight intent checks (handle punctuation like "Hi," or "Thanks!").
        normalized = re.sub(r"[^a-z0-9\s]", " ", (text or "").strip().lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def small_talk_type(text: str) -> str | None:
        text_lower = _normalize_chat_text(text)
        if not text_lower:
            return None

        greetings = {"hello", "hi", "hey"}
        gratitude = {"thanks", "thank you", "appreciate it"}
        acknowledgements = {"ok", "okay", "got it", "great", "cool"}
        farewells = {"bye", "goodbye", "see you"}

        if text_lower in greetings or any(text_lower.startswith(g + " ") for g in greetings):
            return "greeting"
        if text_lower in gratitude or any(text_lower.startswith(g + " ") for g in gratitude):
            return "gratitude"
        if text_lower in farewells or any(text_lower.startswith(f + " ") for f in farewells):
            return "farewell"
        if text_lower in acknowledgements or any(text_lower.startswith(a + " ") for a in acknowledgements):
            return "ack"
        return None

    def _stable_choice(options: list[str], seed: str, *, avoid: str | None = None) -> str:
        """Pick a deterministic-but-varied response without relying on randomness."""
        if not options:
            return ""
        digest = hashlib.md5((seed or "").encode("utf-8"), usedforsecurity=False).digest()
        idx = digest[0] % len(options)
        chosen = options[idx]
        if avoid and len(options) > 1 and chosen.strip() == str(avoid).strip():
            chosen = options[(idx + 1) % len(options)]
        return chosen

    # NOTE: This assistant is intentionally general-purpose (ChatGPT-like).
    # We keep `context` only to improve routing into project-specific analysis
    # modules (recipes/hr/beverage/etc.), not to restrict topics.
    allowed_contexts = {"beverage", "hr", "recipes", "menu", "kpi"}
    prior_messages = _coerce_history_messages(history)
    last_assistant_message = next(
        (m.get("content", "") for m in reversed(prior_messages) if m.get("role") == "assistant"),
        "",
    )
    stype = small_talk_type(prompt)
    if stype == "greeting":
        text_lower = _normalize_chat_text(prompt)
        seed = f"greeting|{text_lower}|{len(prior_messages)}"

        # Treat "how are you / what's up" as a distinct greeting so it doesn't feel canned.
        if re.search(r"\bhow\s+are\s+you\b|\bhow\s+r\s+u\b|\bwhat\s+is\s+up\b|\bwhat\s+s\s+up\b|\bwassup\b|\bhow\s+is\s+it\s+going\b", text_lower):
            return _stable_choice(
                [
                    "I'm doing well—thanks for asking. What would you like to work on today (KPI analysis, staffing, menu, recipes, beverage, or strategy)?",
                    "Doing great—appreciate it. Tell me what you want to analyze today, or upload a CSV and I'll walk through the results.",
                    "All good here. What can I help you with—sales/labor/food cost KPIs, scheduling, menu engineering, recipe costing, or beverage pricing?",
                ],
                seed,
                avoid=last_assistant_message,
            )

        return _stable_choice(
            [
                "Hi! What can I help you with today—KPIs, HR/staffing, menu engineering, recipes, beverage insights, or strategy?",
                "Hello! If you tell me your goal (reduce labor %, improve margins, optimize menu, etc.), I’ll suggest the best next steps.",
                "Hey there. Ask a question or upload a CSV and I’ll analyze it and summarize the key actions.",
                "Welcome back. What are we working on today: sales performance, labor, food cost, menu, recipes, beverage, or planning?",
            ],
            seed,
            avoid=last_assistant_message,
        )
    if stype == "gratitude":
        text_lower = _normalize_chat_text(prompt)
        seed = f"gratitude|{text_lower}|{len(prior_messages)}"
        return _stable_choice(
            [
                "You're welcome. What would you like to work on next?",
                "Happy to help. Want to analyze another area or upload a CSV for deeper insights?",
                "Anytime. What’s the next question you want to tackle?",
            ],
            seed,
            avoid=last_assistant_message,
        )
    if stype == "ack":
        text_lower = _normalize_chat_text(prompt)
        seed = f"ack|{text_lower}|{len(prior_messages)}"
        return _stable_choice(
            [
                "Got it. What would you like to analyze or plan next?",
                "Understood. What’s the next thing you want to look at?",
                "Sounds good—what should we do next?",
            ],
            seed,
            avoid=last_assistant_message,
        )
    if stype == "farewell":
        text_lower = _normalize_chat_text(prompt)
        seed = f"farewell|{text_lower}|{len(prior_messages)}"
        return _stable_choice(
            [
                "Goodbye. If you need help with anything restaurant-related later, just message me.",
                "See you later. When you're back, you can upload a CSV or ask for any analysis.",
                "Take care. I’m here whenever you want to dig into KPIs, staffing, menu, recipes, or beverage insights.",
            ],
            seed,
            avoid=last_assistant_message,
        )

    # Do not block queries by topic; allow any user question.
    # Context (if provided) is used only for routing/optimization.
    if context and context.lower() in allowed_contexts:
        pass

    # If frontend explicitly set a context for recipes, route those requests
    # directly to the KPI/recipe handler first so recipe-specific analysis
    # (costing, scaling, ingredient optimization) is used instead of
    # the more general conversational or KPI food-cost flows.
    prompt_lower = prompt.lower()
    if context == 'recipes' or any(k in prompt_lower for k in ['recipe costing', 'ingredient cost', 'portion cost', 'scale recipe', 'scale recipes', 'analyze recipes']):
        recipe_response = handle_kpi_analysis(prompt)
        if recipe_response:
            return sanitize_response(recipe_response)

    # Route HR analysis before conversational AI so structured reports are returned
    hr_keywords = [
        'training program',
        'training programs',
        'onboarding',
        'skill development',
        'performance tracking',
        'performance management',
        'staff performance',
        'performance analysis',
        'employee performance',
        'staff retention',
        'turnover',
        'labor scheduling',
        'scheduling optimization',
        'shift optimization'
    ]
    if context == 'hr' or any(k in prompt_lower for k in hr_keywords):
        hr_response = handle_kpi_analysis(prompt)
        if hr_response:
            return sanitize_response(hr_response)

    # STEP 1: Try Conversational AI first (natural language queries about menu/business)
    conversational_response = handle_conversational_ai(prompt)
    if conversational_response:
        return sanitize_response(conversational_response)

    # STEP 1.5: If context is beverage or prompt contains beverage keywords, route to beverage analysis
    if context == 'beverage' or any(k in prompt.lower() for k in ['liquor', 'beverage', 'bar inventory', 'drink pricing']):
        beverage_response = handle_beverage_analysis(prompt)
        if beverage_response:
            return sanitize_response(beverage_response)

    # STEP 2: Try specific KPI analysis handlers (legacy keyword-based routing)
    kpi_response = handle_kpi_analysis(prompt)
    if kpi_response:
        return sanitize_response(kpi_response)

    # STEP 3: Fall back to GPT-4 for general hospitality advice
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "Error: OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."

    base_system_message = """You are a helpful, knowledgeable assistant. You answer questions across any topic clearly and accurately, and you can also help with restaurant and hospitality analysis when asked.

CRITICAL FORMATTING RULES - YOU MUST FOLLOW THESE:
1. NEVER use markdown formatting like asterisks, bold, or headers (no **, no ##, no ###)
2. NEVER use LaTeX or mathematical notation (no \\text{}, no \\frac{}, no \\left, no \\right, no backslash commands)
3. NEVER use code blocks or backticks
4. Write in plain, natural English like a human conversation
5. For formulas, write them in simple words: "Food Cost Percentage equals Cost of Goods Sold divided by Total Sales, multiplied by 100"
6. Use natural paragraph structure, not rigid formatting

Your Communication Style:
- Write like you're having a friendly conversation with a restaurant owner
- Use natural paragraphs and sentences
- When listing items, use simple numbered lists (1. 2. 3.) or dashes (-)
- Explain calculations in plain English with the actual numbers
- Be warm, professional, and approachable

When Analyzing Data:
- Acknowledge what the user is asking
- Explain calculations in conversational language with the actual numbers
- Provide 3-5 specific, practical next steps
- Ask a brief follow-up question if key inputs are missing

Remember: Write naturally like a trusted assistant having a conversation. No special formatting, no technical markup, just clear and helpful guidance."""

    try:
        client = OpenAI(api_key=api_key)
        prior_messages = _coerce_history_messages(history)
        messages = [
            {"role": "system", "content": base_system_message},
            *prior_messages,
            {"role": "user", "content": prompt.strip()},
        ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        return sanitize_response(response.choices[0].message.content)

    except Exception as exc:  # pragma: no cover - network/SDK errors
        return f"Error: Unable to process request. {exc}"
