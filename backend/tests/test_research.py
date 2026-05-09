from src.research import extract_result_flag


def test_extract_result_flag_dict_true():
    assert extract_result_flag({"consensus_converged": True}, "consensus_converged") is True


def test_extract_result_flag_dict_false():
    assert extract_result_flag({"consensus_converged": False}, "consensus_converged") is False


def test_extract_result_flag_missing_key():
    assert extract_result_flag({}, "eq_principle_passed") is False


def test_extract_result_flag_stringified_dict():
    s = "{'consensus_converged': True, 'eq_principle_passed': False}"
    assert extract_result_flag(s, "consensus_converged") is True
    assert extract_result_flag(s, "eq_principle_passed") is False


def test_extract_result_flag_non_dict_non_string():
    assert extract_result_flag(None, "x") is False
    assert extract_result_flag(42, "x") is False
