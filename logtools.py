def print_bytes(b_list):
    buffer = ''
    for b in b_list:
        buffer += str(b) + ','
    return buffer.strip(',')
