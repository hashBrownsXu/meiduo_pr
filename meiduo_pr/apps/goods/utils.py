def get_breadcrumb(category):
    """面包屑导航"""
    breadcrumb = {
        'cat1': category.parent.parent,
        'cat2': category.parent,
        'cat3': category
    }

    return breadcrumb

