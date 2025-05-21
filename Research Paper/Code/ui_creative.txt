import streamlit as st
import requests
import urllib.parse
from uuid import uuid4
import re
import os
import streamlit.components.v1 as components

# ------------------ CONFIG ------------------ #
st.set_page_config(page_title="CulinaryFind", page_icon="🍴", layout="wide")

# --- Initialise state  (place near the top) -----------------
if "search_results" not in st.session_state:
    st.session_state["search_results"] = None   # list of recipes or None
if "search_ns" not in st.session_state:
    st.session_state["search_ns"] = "demo"      # namespace for widget keys

FALLBACK_IMG = (
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=60"
)

# ------------------ THEME (CSS) ------------------ #
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        html, body, [class*="st-"]  {font-family:'Poppins',sans-serif;}

        .stApp {background: radial-gradient(circle at 25% 25%, #fffaf0 0%, #fff4e6 25%, #ffeaea 50%, #fff8f8 75%);background-attachment: fixed;}

        .navbar {display:flex;justify-content:space-between;align-items:center;padding:0.6rem 1.2rem;background-color:rgba(255,255,255,0.95);backdrop-filter:blur(6px);border-bottom:1px solid #f1e9e9;box-shadow:0 1px 4px rgba(0,0,0,0.04);position:sticky;top:0;z-index:100;}
        .logo {font-weight:700;font-size:1.35rem;display:flex;align-items:center;gap:0.35rem;color:#ff5e5e;}
        .nav-links a {margin-left:1rem;text-decoration:none;color:#555;font-weight:500;}
        .nav-links a:hover {color:#ff5e5e;}

        .card {border:1px solid #f5e8e8;border-radius:14px;padding:0.8rem;background:rgba(255,255,255,0.92);box-shadow:0 4px 14px rgba(0,0,0,0.06);transition:transform 0.15s ease, box-shadow 0.15s ease;cursor:pointer;}
        .card:hover {transform:translateY(-4px);box-shadow:0 6px 18px rgba(0,0,0,0.08);}        
        .card img {border-radius:10px;object-fit:cover;height:180px;width:100%;}
        .stButton>button {border:none;background:none;padding:0;margin:0;width:100%;text-align:left;}
        
        /* Style for the "Search 🔍" button (first button in the form) */
        div.search-zone button[data-testid="stFormSubmitButton"]:nth-child(1) {
            background: #ff844c !important;
            color: #fff !important;
        }

        /* Style for the "🎲 Surprise me" button (second button in the form) */
        div.search-zone button[data-testid="stFormSubmitButton"]:nth-child(2) {
            background: #ff844c !important;
            color: #fff !important;
        }
        .detail-wrapper {border-radius:18px;background-color:rgba(255,255,255,0.95);padding:2rem;box-shadow:0 6px 18px rgba(0,0,0,0.08);}        
        .badge {display:inline-block;padding:0.25rem 0.55rem;margin:0.15rem;border-radius:10px;background:#ffe4e4;font-size:0.75rem;font-weight:600;color:#ff5e5e;white-space:nowrap;}
        .step {margin-bottom:0.65rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------ NAV BAR ------------------ #
st.markdown(
    """
    <div class="navbar">
        <div class="logo">🍴 CulinaryFind</div>
        <div class="nav-links">
            <a href="#">Home</a>
            <a href="#">Recipes</a>
            <a href="#">About</a>
            <a href="#">Contact</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------ HELPERS ------------------ #
@st.cache_data(show_spinner=False)
def fetch_recipes(ingredients_list):
    if not ingredients_list:
        return []
    base_url = "http://localhost:5000/search"
    params = [("ingredients", ing) for ing in ingredients_list]
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    try:
        os.write(1, f"URL GENERATED : {url}\n".encode())
        resp = requests.get(url, timeout=80)
        resp.raise_for_status()
        data = resp.json()
        print(f"Raw API response: {data}")  # Debugging
        results = data.get("results", [])
        return results if results else demo_recipes  # Fall back to demo data
    except Exception as e:
        st.error(f"Could not retrieve recipes – {e}")
        return demo_recipes  # Fall back to demo data


# ---------------SURPRISE ME -----------------#
@st.cache_data(show_spinner=False, ttl=300)
def fetch_surprise_recipe(ingredients):
    """
    Ask the AI endpoint for ONE recipe.
    `ingredients` is a list of plain strings (may be empty).
    """
    os.write(1, f"INGREDIENTS BEFORE URL GENERATED : {ingredients}\n".encode())
    if isinstance(ingredients, str):
        if ' ' in ingredients.strip():
            ingredients = ingredients.split(" ")
        else:
            ingredients = list(ingredients)
    base = "http://localhost:5000/surprise"
    query = urllib.parse.urlencode([("ingredients", ing) for ing in ingredients])
    url   = f"{base}?{query}" if query else base

    try:
        os.write(1, f"URL GENERATED : {url}\n".encode())
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        data = r.json()
        os.write(1, f"Raw API response: {data}\n".encode())
        print(f"Raw API response: {data}")         # backend returns {"recipe": {...}}
        results = data.get("results", [])
        return results if results else demo_recipes  # Fall back to demo data
    except Exception as e:
        st.error(f"Couldn’t get a surprise recipe – {e}")
        return demo_recipes

def reset_selection():
    if "selected_recipe" in st.session_state:
        del st.session_state["selected_recipe"]


def clickable_card(recipe, search_ns):
    key_base = f"{search_ns}_{recipe['id']}"
    clicked = False

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Image overlay button (an invisible button before image)
        if st.button("", key=f"img_{key_base}"):
            clicked = True
        st.image(recipe.get("image_url") or FALLBACK_IMG, use_container_width=True)

        # Title button
        if st.button(recipe["name"].title(), key=f"name_{key_base}"):
            clicked = True

        meta = f"⏱️ {recipe.get('prep_time', '?')} min · {len(recipe.get('ingredients', []))} ingredients"
        st.caption(meta)

        # Description
        if recipe.get("description"):
            st.caption(recipe["description"])

        st.markdown('</div>', unsafe_allow_html=True)

    return clicked


def render_recipes(recipes, heading, search_ns):
    st.subheader(heading)
    if not recipes:
        st.info("No recipes found. Try a different combination of ingredients.")
        return

    cols_per_row = 3
    for i in range(0, len(recipes), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, recipe in zip(cols, recipes[i:i + cols_per_row]):
            with col:
                if clickable_card(recipe, search_ns):
                    st.session_state["selected_recipe"] = recipe
                    st.rerun()  # Trigger rerun to display recipe details

def _nutrition_rows(nutrition):
    if not nutrition:
        return ""
    return "\n".join(f"| {k.replace('_', ' ').title()} | {v} |" for k, v in nutrition.items())


def render_recipe_details(recipe):
    st.markdown('<div class="detail-wrapper">', unsafe_allow_html=True)
    st.header(recipe.get("name", "Unnamed Recipe").title())
    if recipe.get("description"):
        st.caption(recipe["description"])

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Ingredients")
        for ing in recipe.get("ingredients", []):
            st.markdown(f"<span class='badge'>{ing}</span>", unsafe_allow_html=True)

        st.subheader("Steps")
        for idx, step in enumerate(recipe.get("steps", []), 1):
            st.markdown(f"<div class='step'><strong>Step {idx}:</strong> {step}</div>", unsafe_allow_html=True)

    with right:
        st.image(recipe.get("image_url") or FALLBACK_IMG, use_container_width=True)
        if recipe.get("nutrition"):
            st.subheader("Nutrition (per serving)")
            table_rows = _nutrition_rows(recipe["nutrition"])
            st.markdown("| Metric | Value |\n|---|---|\n" + table_rows)

    if recipe.get("tags"):
        st.write("\n")
        st.subheader("Tags")
        st.markdown(
            "".join(
                f"<span class='badge'>{tag}</span>" for tag in recipe["tags"][:30]
            ),
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    st.write("\n")
    if st.button("← Back to results"):
        reset_selection()
        st.rerun()

# ------------------ DEMO DATA ------------------ #
demo_recipes = [
    {
      "cuisine": "",
      "description": "serve with mixed greens, goats cheese, beets (red or golden) or raspberries.  from the organic authority.",
      "id": 25200,
      "image_url": "https://unsplash.com/photos/whldb_oMSgA/download?ixid=M3wxMjA3fDB8MXxzZWFyY2h8MTU2fHxCbG9vZCUyME9yYW5nZSUyMCUyMGRyaW5rfGVufDB8MHx8fDE3NDY1MTY4NzV8MA&force=true",
      "ingredients": [
        "blood orange juice",
        "shallot",
        "fresh thyme leave",
        "balsamic vinegar",
        "orange zest",
        "almond oil",
        "extra virgin olive oil",
        "sea salt",
        "fresh ground black pepper"
      ],
      "ingredients_tokenized": [
        "blood orange juice",
        "shallot",
        "fresh thyme leave",
        "balsamic vinegar",
        "orange zest",
        "almond oil",
        "extra virgin olive oil",
        "sea salt",
        "fresh ground black pepper"
      ],
      "name": "blood orange almond vinaigrette",
      "nutrition": {
        "calories": "1095.9",
        "protein": "167.0",
        "saturated_fat": "93.0",
        "sodium": "0.0",
        "sugar": "4.0",
        "total_fat": "59.0"
      },
      "prep_time": "20",
      "source": "big_csv.csv",
      "steps": [
        "bring blood orange juice to a boil in medium saucepan",
        "lower heat to a simmer and reduce until you have 1 / 3 cup of blood orange juice",
        "in a medium bowl , combine reduced blood orange juice , vinegar , shallot , thyme and blood orange zest",
        "slowly drizzle oils into mixture while whisking until combined and thick",
        "season with salt and pepper to taste",
        "refrigerate until needed"
      ],
      "tags": [
        "30-minutes-or-less",
        "time-to-make",
        "course",
        "cuisine",
        "preparation",
        "north-american",
        "salads",
        "condiments-etc",
        "american",
        "easy",
        "salad-dressings",
        "californian",
        "3-steps-or-less"
      ]
    },
    {
      "cuisine": "",
      "description": "the original of this recipe was found online at goneraw, but i tweaked it a little. i've used a rounded 2-up measure of frozen peaches for this.",
      "id": 37151,
      "image_url": "https://unsplash.com/photos/SCcHQRI773s/download?ixid=M3wxMjA3fDB8MXxzZWFyY2h8Mnx8Y2Fycm90JTIwJTIwcGVhY2glMjBhbmQlMjBmcmVzaCUyMHRoeW1lJTIwc21vb3RoaWUlMjAlMjByYXclMjBmb29kfGVufDB8fHx8MTc0NjUxNjE5M3ww&force=true?auto=format&fit=crop&w=800&q=60",
      "image_url1": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?ixid=M3w3NDYxODR8MHwxfHNlYXJjaHwxfHxjaGlja2VuJTIwdGlra2ElMjBtYXNhbGF8ZW58MHwwfHx8MTc0NjUxNzE2MXww&ixlib=rb-4.1.0",
      "ingredients": [
        "carrots",
        "fresh peaches",
        "orange, juice of",
        "water",
        "fresh thyme"
      ],
      "ingredients_tokenized": [
        "carrots",
        "fresh peaches",
        "orange, juice of",
        "water",
        "fresh thyme"
      ],
      "name": "carrot  peach and fresh thyme smoothie  raw food",
      "nutrition": {
        "calories": "132.6",
        "protein": "1.0",
        "saturated_fat": "80.0",
        "sodium": "5.0",
        "sugar": "5.0",
        "total_fat": "0.0"
      },
      "prep_time": "5",
      "source": "big_csv.csv",
      "steps": [
        "process the carrots in a juicer & use the resulting juice for this drink",
        "in a blender process all ingredients until smooth"
      ],
      "tags": [
        "15-minutes-or-less",
        "time-to-make",
        "course",
        "main-ingredient",
        "preparation",
        "for-1-or-2",
        "5-ingredients-or-less",
        "beverages",
        "fruit",
        "vegetables",
        "easy",
        "vegan",
        "vegetarian",
        "smoothies",
        "dietary",
        "pitted-fruit",
        "peaches",
        "carrots",
        "number-of-servings",
        "3-steps-or-less"
      ]
    },
    {
      "cuisine": "",
      "description": "refreshing, lovely dessert.  try to use fresh juice if you can. serve in recipe #222997.",
      "id": 149478,
      "image_url": "https://unsplash.com/photos/tGrudeNNGSE/download?ixid=M3wxMjA3fDB8MXxzZWFyY2h8M3x8b3JhbmdlJTIwdGh5bWUlMjBncmFuaXRhJTIwZHJpbmt8ZW58MHx8fHwxNzQ2NTE2MzM0fDA&force=true?auto=format&fit=crop&w=800&q=60",
      "ingredients": [
        "orange juice",
        "lemon juice",
        "splenda sugar substitute",
        "fresh thyme"
      ],
      "ingredients_tokenized": [
        "orange juice",
        "lemon juice",
        "splenda sugar substitute",
        "fresh thyme"
      ],
      "name": "orange thyme granita",
      "nutrition": {
        "calories": "51.7",
        "protein": "0.0",
        "saturated_fat": "36.0",
        "sodium": "0.0",
        "sugar": "1.0",
        "total_fat": "0.0"
      },
      "prep_time": "122",
      "source": "big_csv.csv",
      "steps": [
        "combine juices , sugar and thyme in medium bowl",
        "if using sugar , stir until dissolved",
        "freeze until slightly firm , about 1 hour",
        "beat with wire whisk to break ice crystals",
        "repeat freezing and beating process 2-3 times until ice is firm and granular"
      ],
      "tags": [
        "time-to-make",
        "course",
        "preparation",
        "5-ingredients-or-less",
        "desserts",
        "easy",
        "4-hours-or-less"
      ]
    },
    {
      "cuisine": "",
      "description": "i have not tried this, but thought i'd post this for anyone thinking of making a goose for christmas. this looks so easy! this is courtesy of the ",
      "id": 174793,
      "image_url": "https://unsplash.com/photos/iNpOEYHe7NM/download?ixid=M3wxMjA3fDB8MXxzZWFyY2h8Mnx8Um9hc3QlMjBHb29zZSUyMFdpdGglMjBDaXRydXMlMjBBbmQlMjBIZXJic3xlbnwwfHx8fDE3NDY1MTY0MzZ8MA&force=true",
      "ingredients": [
        "goose",
        "fresh thyme",
        "fresh rosemary",
        "salt",
        "pepper",
        "orange",
        "lime"
      ],
      "ingredients_tokenized": [
        "goose",
        "fresh thyme",
        "fresh rosemary",
        "salt",
        "pepper",
        "orange",
        "lime"
      ],
      "name": "roast goose with citrus and herbs",
      "nutrition": {
        "calories": "1114.3",
        "protein": "121.0",
        "saturated_fat": "8.0",
        "sodium": "42.0",
        "sugar": "182.0",
        "total_fat": "123.0"
      },
      "prep_time": "70",
      "source": "big_csv.csv",
      "steps": [
        "preheat oven to 500",
        "remove giblets and neck from goose",
        "remove excess fat from main cavity of goose",
        "rinse goose inside and out with cold water",
        "pat dry with paper towels",
        "combine thyme , rosemary , salt and pepper in small bowl",
        "place goose , breast side down on a rack in a roasting pan",
        "sprinkle goose with half of herb mixture",
        "place orange and lime wedges in cavity of goose",
        "turn goose so that breast side is up",
        "sprinkle remaining herbs over goose",
        "roast goose 1 hour",
        "turn off oven and let goose stand in oven 45 minutes remove goose from oven",
        "cover and let rest 10 minutes",
        "slice and serve"
      ],
      "tags": [
        "time-to-make",
        "course",
        "main-ingredient",
        "cuisine",
        "preparation",
        "occasion",
        "north-american",
        "main-dish",
        "poultry",
        "american",
        "oven",
        "holiday-event",
        "dietary",
        "christmas",
        "meat",
        "goose",
        "equipment",
        "4-hours-or-less"
      ]
    },
    {
      "cuisine": "",
      "description": "it's good",
      "id": 29914,
      "image_url": "https://unsplash.com/photos/bpPTlXWTOvg/download?ixid=M3wxMjA3fDB8MXxzZWFyY2h8Mnx8Y29va2VkJTIwc2FsbW9ufGVufDB8fHx8MTc0NjUxNjUxOHww&force=true",
      "ingredients": [
        "salmon fillets",
        "soy sauce",
        "bay leaf",
        "fresh thyme sprig"
      ],
      "ingredients_tokenized": [
        "salmon fillets",
        "soy sauce",
        "bay leaf",
        "fresh thyme sprig"
      ],
      "name": "broiled salmon fillet with mustard dill sauce",
      "nutrition": {
        "calories": "219.8",
        "protein": "10.0",
        "saturated_fat": "0.0",
        "sodium": "5.0",
        "sugar": "75.0",
        "total_fat": "5.0"
      },
      "prep_time": "30",
      "source": "big_csv.csv",
      "steps": [
        "preheat broiler",
        "rinse salmon and pat dry",
        "arrange salmon , skin side down , in a foil-lined jelly-roll pan and rub thoroughly with soy sauce",
        "season salmon with salt and pepper and broil about 4 inches from heat 12 to 15 minutes , or until just cooked through",
        "transfer salmon to a platter and garnish with herbs",
        "serve salmon warm or at room temperature with mustard dill sauce"
      ],
      "tags": [
        "30-minutes-or-less",
        "time-to-make",
        "course",
        "main-ingredient",
        "preparation",
        "healthy",
        "5-ingredients-or-less",
        "very-low-carbs",
        "main-dish",
        "seafood",
        "easy",
        "salmon",
        "fish",
        "dietary",
        "low-sodium",
        "low-saturated-fat",
        "low-calorie",
        "high-protein",
        "low-carb",
        "high-in-something",
        "low-in-something",
        "saltwater-fish"
      ]
    }
]


def style_button(label: str,
                 *,
                 font_color: str = "#ffffff",
                 background_color: str = "#ff844c"):
    """
    Find the first <button> whose innerText exactly matches `label`
    and overwrite its colour & background.

    Works once per rerun; call it after the buttons are on the page.
    """
    components.html(
        f"""
        <script>
            const btns = window.parent.document.querySelectorAll('button');
            btns.forEach(btn => {{
                if (btn.innerText.trim() === `{label}`) {{
                    btn.style.color = `{font_color}`;
                    btn.style.background = `{background_color}`;
                    btn.style.borderRadius = '50px';
                    btn.style.fontWeight = 600;
                    btn.style.height = '3.2rem';
                    btn.style.width = '12rem';
                    btn.style.padding = '0 2rem';
                    btn.style.transition = 'background .2s, transform .1s';
                }}
            }});
        </script>
        """,
        height=0, width=0,
    )



# ------------------ HERO ------------------ #
if "selected_recipe" not in st.session_state:
    st.markdown("## Discover Your Perfect Recipe ✨")
    st.caption("Search thousands of delicious recipes by ingredients you already have! 💡")

# ------------------ SEARCH FORM ------------------ #


with st.form(key="search_form", clear_on_submit=False):
    user_query = st.text_input(
        "Enter ingredients (comma-separated)",
        placeholder="e.g. chicken, bell pepper, corn",
    )
    submitted = st.form_submit_button("Search 🔍")
    surprise_click = st.form_submit_button("🎲 Surprise me")


style_button("Search 🔍")
style_button("🎲 Surprise me")
# -- SURPRISE ME -------------------------------------------------------------
# --- SURPRISE ME -----------------------------------------------------------


if surprise_click:
    raw = user_query.strip()                       # what’s in the text box now
    ingredients = (
        [part.strip() for part in re.split(r"[,\s]+", raw) if part.strip()]
        if raw else []
    )

    reset_selection()
    with st.spinner("Cooking up something special…"):
        results = fetch_surprise_recipe(ingredients)   # <- pass list here
    st.session_state["search_results"] = results
    st.session_state["search_ns"] = str(uuid4())
    # st.rerun()                            # show the new recipe immediately

if submitted and user_query:
    # Fresh search ⇒ wipe any previous selections
    reset_selection()

    ingredients = [x.strip() for x in user_query.split(",") if x.strip()]
    if len(ingredients) == 1:
        single = ingredients[0]           # the only element
        if " " in single:
            ingredients = [x.strip() for x in single.split(" ") if x.strip()]
    with st.spinner("Searching …"):
        results = fetch_recipes(ingredients)

    # 🔑 Persist the results **and** a stable namespace
    st.session_state["search_results"] = results
    st.session_state["search_ns"] = str(uuid4())

# ------------------ MAIN ROUTING ------------------ #
# ------------------ MAIN ROUTING ------------------ #
if "selected_recipe" in st.session_state:
    # detail page
    render_recipe_details(st.session_state["selected_recipe"])

else:
    # results page
    results = st.session_state["search_results"] or demo_recipes
    ns      = st.session_state["search_ns"]      # 'demo' if no search yet
    heading = "Your Recipes" if st.session_state["search_results"] else "Popular Recipes"
    render_recipes(results, heading, ns)