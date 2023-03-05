def get_top_keys(keys, values):
    """get keys with the top value, sorted by the values list from large to small

    Args:
        keys (list): a list of keys
        values (list): a list of values, should be as long as the keys
    
    Returns:
        top_keys (list)
    """
    dict_t = dict(zip(keys, values))
    dict_t = dict(sorted(dict_t.items(), key=lambda item: -item[1]))
    sorted_keys = list(dict_t.keys())
    
    top_num = 0
    top_value = dict_t[sorted_keys[0]]
    while top_num<len(keys) and top_value == dict_t[sorted_keys[top_num]]:
        top_num += 1
    
    return sorted_keys[:top_num]