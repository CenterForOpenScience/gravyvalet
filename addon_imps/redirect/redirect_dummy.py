from addon_toolkit.imp import AddonImp


class DummyRedirectImp(AddonImp):
    """this is a dummy AddonImp for ALL redirect services. 
    redirect links will be specified in django admin configuration."""
    pass