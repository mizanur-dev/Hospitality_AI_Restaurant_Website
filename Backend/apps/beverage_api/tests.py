from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase


class BeverageUploadRoutingTests(TestCase):
    def _post_csv(self, *, csv_text: str, filename: str, analysis_type: str | None = None):
        payload = {}
        if analysis_type is not None:
            payload["analysis_type"] = analysis_type

        upload = SimpleUploadedFile(
            filename,
            csv_text.encode("utf-8"),
            content_type="text/csv",
        )

        return self.client.post(
            "/api/beverage/upload/",
            data={**payload, "required_csv": upload},
        )

    def test_inventory_csv_routes_even_if_wrong_analysis_type(self):
        csv_text = (
            "current_stock,reorder_point,monthly_usage,inventory_value,lead_time_days,safety_stock,item_cost,target_turnover\n"
            "800,250,600,12500,7,100,12.5,12\n"
        )

        # Purposely send a mismatched analysis_type.
        res = self._post_csv(
            csv_text=csv_text,
            filename="bar_inventory.csv",
            analysis_type="liquor_cost_analysis",
        )

        self.assertEqual(res.status_code, 200)
        self.assertIn("html_response", res.json())
        self.assertIn("Bar Inventory Analysis", res.json()["html_response"])
        self.assertNotIn("Missing required columns", res.json()["html_response"])

    def test_pricing_csv_routes_even_if_wrong_analysis_type(self):
        csv_text = (
            "drink_price,cost_per_drink,sales_volume,competitor_price,target_margin,market_position,elasticity_factor\n"
            "12,3,1800,11,75,premium,1.5\n"
        )

        res = self._post_csv(
            csv_text=csv_text,
            filename="beverage_pricing.csv",
            analysis_type="liquor_cost_analysis",
        )

        self.assertEqual(res.status_code, 200)
        self.assertIn("html_response", res.json())
        self.assertIn("Beverage Pricing Analysis", res.json()["html_response"])
        self.assertNotIn("Missing required columns", res.json()["html_response"])
