import json
from collections import defaultdict

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_compliance(data):
    results = []
    overall_stats = {
        "total_sites": 0,
        "sites_with_email": 0,
        "sites_with_phone": 0,
        "total_forms": 0,
        "total_keywords": defaultdict(int),
        "keyword_category_counts": defaultdict(int),
        "average_url_depth": 0
    }
    total_url_depths = []
    
    for site_data in data:
        for site, details in site_data.items():
            overall_stats["total_sites"] += 1
            analysis = {"site": site}
            
            # Extract contact details
            has_email = bool(details.get("emails"))
            has_phone = bool(details.get("phonenumbers"))
            analysis["has_email"] = has_email
            analysis["has_phone"] = has_phone
            
            if has_email:
                overall_stats["sites_with_email"] += 1
            if has_phone:
                overall_stats["sites_with_phone"] += 1
            
            # Keyword Frequency Analysis
            keyword_counts = defaultdict(int)
            if "keywordcount_versions" in details and details["keywordcount_versions"]:
                keyword_dict = details["keywordcount_versions"][0]  # Only one dict in list
                for category, keywords in keyword_dict.items():
                    overall_stats["keyword_category_counts"][category] += 1  # Count category occurrences
                    for keyword, count in keywords.items():
                        keyword_counts[keyword] += count
                        overall_stats["total_keywords"][keyword] += count
            analysis["keyword_counts"] = dict(keyword_counts)
            
            # Form Availability
            forms_data = details.get("forms_data_versions", [])
            form_count = sum(sum(form.values()) for form in forms_data) if forms_data else 0
            analysis["form_count"] = form_count
            overall_stats["total_forms"] += form_count
            
            # URL Depth Analysis
            if "urls_with_text_versions" in details:
                depth_counts = [len(outer.keys()) for outer in details["urls_with_text_versions"]]
                avg_url_depth = sum(depth_counts) / len(depth_counts) if depth_counts else 0
            else:
                avg_url_depth = 0
            
            analysis["avg_url_depth"] = avg_url_depth
            total_url_depths.append(avg_url_depth)
            
            results.append(analysis)
    
    # Compute overall average URL depth
    overall_stats["average_url_depth"] = sum(total_url_depths) / len(total_url_depths) if total_url_depths else 0
    overall_stats["total_keywords"] = dict(overall_stats["total_keywords"])
    overall_stats["keyword_category_counts"] = dict(overall_stats["keyword_category_counts"])
    
    return results, overall_stats

if __name__ == "__main__":
    json_file = "results/scraped_results.json"  # Replace with actual file path
    data = load_json(json_file)
    compliance_results, overall_analysis = analyze_compliance(data)
    
    # Save results to a JSON file
    output = {"site_analysis": compliance_results, "overall_analysis": overall_analysis}
    with open("compliance_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)
    
    print("Analysis complete. Results saved to compliance_results.json")
