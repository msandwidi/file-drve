
def is_valid_int(s):
    """
    Check whether a number
    is avalid int or not
    """
    
    if not s:
        return False
    
    try:
        int(s)
        return True
    except ValueError:
        return False
    
