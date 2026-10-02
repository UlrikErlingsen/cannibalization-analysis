"""Verified primary-source references and concise original method notes."""
SOURCES = [
    {
        "title": "Menu engineering re-engineered: Accounting for menu item substitutes in pricing and menu placement decisions",
        "authors": "Breffni M. Noone and Guillaume Cachia", "year": 2020,
        "url": "https://doi.org/10.1016/j.ijhm.2020.102504",
        "access": "https://pure.psu.edu/en/publications/menu-engineering-re-engineered-accounting-for-menu-item-substitut/",
        "evidence": "Peer-reviewed restaurant study; abstract and bibliographic record verified.",
        "finding": "A study of 48 steakhouse outlets uses own- and cross-price elasticities to account for substitution in menu pricing and placement.",
        "application": "Evaluate changes across the whole comparable menu set and its economics. The app does not reproduce or estimate this paper's elasticity model.",
    },
    {
        "title": "Estimating Cannibalization Rates for Pioneering Innovations",
        "authors": "Harald J. van Heerde, Shuba Srinivasan and Marnik G. Dekimpe", "year": 2010,
        "url": "https://doi.org/10.1287/mksc.1100.0575",
        "access": "https://pubsonline.informs.org/doi/10.1287/mksc.1100.0575",
        "evidence": "Peer-reviewed Marketing Science article; abstract verified.",
        "finding": "New-product sales can come from a firm's existing products, competitors or category expansion. The paper models these sources using automobile transaction data.",
        "application": "Separate launch volume from portfolio incrementality. Our own-sales data cannot separate competitive switching from category growth; they remain combined.",
    },
    {
        "title": "Discrete Choice Methods with Simulation, second edition",
        "authors": "Kenneth E. Train", "year": 2009,
        "url": "https://eml.berkeley.edu/books/choice2.html",
        "access": "https://eml.berkeley.edu/books/choice2.html",
        "evidence": "Author-hosted academic textbook with chapters on logit, GEV, mixed logit and endogeneity.",
        "finding": "Discrete-choice models offer a framework for estimating demand across alternatives. Model assumptions govern predicted substitution patterns.",
        "application": "A future extension could use choice experiments to estimate switching. Today's overlap weights are user assumptions, not fitted consumer preferences.",
    },
    {
        "title": "How Much Should We Trust Differences-In-Differences Estimates?",
        "authors": "Marianne Bertrand, Esther Duflo and Sendhil Mullainathan", "year": 2004,
        "url": "https://doi.org/10.1162/003355304772839588",
        "access": "https://users.nber.org/~confer/2001/si2001/bertrand.pdf",
        "evidence": "Peer-reviewed Quarterly Journal of Economics article; publisher abstract and NBER working-paper version.",
        "finding": "Serial correlation can make conventional difference-in-differences uncertainty estimates misleading.",
        "application": "Resample entire locations, keeping their periods and items together. Few locations still produce fragile intervals; a bootstrap does not repair a weak study design.",
    },
    {
        "title": "CausalImpact: assumptions for a counterfactual time-series analysis",
        "authors": "Google CausalImpact documentation; Brodersen et al. research", "year": 2015,
        "url": "https://google.github.io/CausalImpact/CausalImpact.html",
        "access": "https://google.github.io/CausalImpact/CausalImpact.html",
        "evidence": "Official method documentation, linked to the peer-reviewed 2015 article.",
        "finding": "Controls must be unaffected by the intervention, and the relationship learned before the intervention must remain useful afterward.",
        "application": "Check control contamination and concurrent changes. This app uses a two-group comparison, not the CausalImpact Bayesian model.",
    },
]

LIMITS = [
    "Cannibalization means displacement of your own existing demand; it can still improve contribution when the new item's margin is higher.",
    "Menu mode covers alternatives within a comparable meal occasion, such as mains. Bundles, shared dishes, sides and basket complements need a basket-level design.",
    "Product units must be comparable. Convert different pack sizes into equivalent units before upload, or interpret revenue and contribution instead of unit rates.",
    "A before/after drop or a negative correlation alone is not evidence of cannibalization. Seasonality, stockouts, price changes and promotions can produce the same pattern.",
    "Historical net displacement is an aggregate contrast, not observed customer switching. Halo and losses can offset; rates may be below 0% or above 100% and are not clipped.",
    "The planner conserves volume and assumes one displaced incumbent unit per cannibalized launch unit. It does not estimate demand, price elasticity, customer traffic or capacity effects.",
    "Contribution equals units times price minus variable unit cost, then declared incremental launch cost. It excludes undeclared waste, labor, channel fees, tax and fixed overhead.",
]
