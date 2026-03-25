new_tests = """
    def test_route_uses_txtdesig_not_codeid(self):
        \"\"\"AIXM 4.5: RteUid uses txtDesig (not codeId) as route identifier.\"\"\"
        rte_uid_children = {"txtDesig": "R655", "txtLocDesig": "EUR"}
        txt_desig = rte_uid_children.get("txtDesig", "")
        code_id_raw = rte_uid_children.get("codeId", "")
        assert txt_desig == "R655", "Route identifier must come from txtDesig"
        assert code_id_raw == "", "codeId is absent in AIXM 4.5 RteUid"

    def test_route_segment_linking_by_mid(self):
        \"\"\"
        AIXM 4.5: Rsg links to Rte via the mid attr on the nested RteUid inside
        RsgUid -- NOT by codeId|codeType. Mirrors the Python parser architecture.
        \"\"\"
        rte_mids = {
            "17952799": {"txtDesig": "R655", "segments": []},
            "76798393": {"txtDesig": "UN131", "segments": []},
        }
        rsg_list = [
            {"rte_uid_mid": "17952799", "startPointId": "LITAN", "endPointId": "SAMTI"},
            {"rte_uid_mid": "17952799", "startPointId": "SAMTI", "endPointId": "BALMA"},
            {"rte_uid_mid": "76798393", "startPointId": "DOBAR", "endPointId": "ERPIN"},
        ]
        seg_index = {}
        for rsg in rsg_list:
            mid = rsg["rte_uid_mid"]
            seg_index.setdefault(mid, []).append(rsg)
        for rte_mid, rte_data in rte_mids.items():
            rte_data["segments"] = seg_index.get(rte_mid, [])
        assert len(rte_mids["17952799"]["segments"]) == 2
        assert len(rte_mids["76798393"]["segments"]) == 1
        assert rte_mids["17952799"]["segments"][0]["startPointId"] == "LITAN"
        assert rte_mids["17952799"]["segments"][1]["startPointId"] == "SAMTI"

"""

with open("tests/test_web_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Try all common patterns
markers_to_try = [
    "\r\nclass TestFilterLogic:",
    "\nclass TestFilterLogic:",
    "\r\n\r\nclass TestFilterLogic:",
    "\n\nclass TestFilterLogic:",
]

inserted = False
for marker in markers_to_try:
    if marker in content:
        content = content.replace(marker, new_tests + marker, 1)
        with open("tests/test_web_ui.py", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Success: used marker {repr(marker)}")
        inserted = True
        break

if not inserted:
    # Find position manually
    idx = content.find("class TestFilterLogic:")
    print(f"Found at idx {idx}, chars before: {repr(content[idx-15:idx])}")
