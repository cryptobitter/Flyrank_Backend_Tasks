"""
Corpus & Evaluation Dataset Generator.

Generates:
- 45 physical sample images in data/images/
- data/corpus_metadata.json with structured vision descriptions
- data/eval_dataset.json with 12 labeled evaluation test cases
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(CURRENT_DIR, "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

CATEGORIES = {
    "fox": {
        "count": 8,
        "subject": "red fox",
        "category": "animal",
        "color": (217, 83, 30),
        "attrs": ["orange fur", "bushy tail", "wild", "forest", "Vulpes vulpes"],
        "captions": [
            "A wild red fox standing alert in a temperate forest",
            "A European red fox (Vulpes vulpes) hunting in autumn woodland",
            "A young red fox curled up in tall grass",
            "Close-up of a red fox with vibrant orange coat and white chest",
            "A red fox trotting through snowy pine trees",
            "Red fox foraging along the forest edge at dusk",
            "An urban red fox peering through leafy underbrush",
            "A red fox family playing near their woodland den",
        ],
    },
    "wolf": {
        "count": 8,
        "subject": "gray wolf",
        "category": "animal",
        "color": (100, 110, 120),
        "attrs": ["gray coat", "pack predator", "wild", "snow", "Canis lupus"],
        "captions": [
            "A gray wolf standing atop a rocky ridge in winter",
            "Timber wolf (Canis lupus) leading its pack through northern tundra",
            "Portrait of an arctic wolf with piercing yellow eyes",
            "A lone gray wolf howling in a pine wilderness",
            "Two gray wolves resting together in the snow",
            "A gray wolf stalking prey through dense boreal forest",
            "Alpha gray wolf patrolling pack territory boundaries",
            "A gray wolf drinking from a frozen mountain creek",
        ],
    },
    "dog": {
        "count": 8,
        "subject": "golden retriever",
        "category": "animal",
        "color": (230, 180, 80),
        "attrs": ["golden fur", "domestic canine", "friendly pet", "yard", "Canis familiaris"],
        "captions": [
            "A friendly golden retriever dog sitting on a sunny lawn",
            "Domestic retriever fetching a yellow tennis ball in the park",
            "A happy golden dog smiling with tongue out",
            "Family dog resting comfortably on a living room rug",
            "A golden retriever puppy exploring the garden",
            "A domestic pet dog playing with children outdoors",
            "Golden retriever waiting loyally beside its owner",
            "A fluffy retriever swimming in a calm lake",
        ],
    },
    "bear": {
        "count": 8,
        "subject": "grizzly bear",
        "category": "animal",
        "color": (92, 64, 51),
        "attrs": ["brown fur", "large mammal", "river", "salmon", "Ursus arctos"],
        "captions": [
            "A massive grizzly bear catching salmon at a river waterfall",
            "North American brown bear (Ursus arctos) wandering through subalpine meadow",
            "A female grizzly bear protecting two small cubs in Alaskan wilderness",
            "Grizzly bear foraging for summer berries along a creek",
            "Large brown bear digging roots in the autumn hillside",
            "Grizzly bear standing tall on hind legs in the river",
            "A coastal brown bear shaking water from its heavy coat",
            "Grizzly bear walking through misty evergreen valley",
        ],
    },
    "deer": {
        "count": 8,
        "subject": "white-tailed deer",
        "category": "animal",
        "color": (160, 120, 80),
        "attrs": ["antlers", "herbivore", "meadow", "grazing", "Odocoileus virginianus"],
        "captions": [
            "A white-tailed deer buck with large antlers standing in a meadow",
            "Mother deer with twin spotted fawns in morning sunlight",
            "A cautious doe looking over its shoulder in a deciduous grove",
            "White-tailed buck leaping across a countryside stone wall",
            "Deer grazing peaceful wildflowers at sunrise",
            "A graceful white-tailed deer drinking at a forest stream",
            "Buck in autumn foliage displaying velvet antlers",
            "Deer family moving quietly through winter birch woods",
        ],
    },
    "tech": {
        "count": 3,
        "subject": "cloud datacenter",
        "category": "technology",
        "color": (30, 41, 59),
        "attrs": ["server rack", "network cables", "LEDs", "infrastructure", "cloud computing"],
        "captions": [
            "Rows of illuminated server racks in a modern enterprise datacenter",
            "High-speed fiber optic networking cables connected to switchboard",
            "Cloud computing server room with blue LED status indicators",
        ],
    },
    "blurry": {
        "count": 2,
        "subject": "unclear shadow",
        "category": "unclassified",
        "color": (60, 60, 60),
        "attrs": ["blurry", "low light", "heavy noise", "indistinct"],
        "captions": [
            "An indistinct dark shape heavily obscured by thick fog and camera blur",
            "Underexposed grainy silhouette with severe motion blur and no clear features",
        ],
    },
}


def build_corpus():
    metadata_list = []

    for cat_name, cat_data in CATEGORIES.items():
        for i in range(1, cat_data["count"] + 1):
            image_id = f"{cat_name}_{i:02d}"
            filename = f"{image_id}.jpg"
            img_path = os.path.join(IMAGES_DIR, filename)

            # Generate synthetic test image file using Pillow
            img = Image.new("RGB", (400, 300), color=cat_data["color"])
            draw = ImageDraw.Draw(img)
            draw.rectangle([10, 10, 390, 290], outline=(255, 255, 255), width=2)
            draw.text((25, 25), f"ID: {image_id}", fill=(255, 255, 255))
            draw.text((25, 50), f"Subject: {cat_data['subject']}", fill=(255, 255, 255))
            draw.text((25, 75), f"Category: {cat_data['category']}", fill=(255, 255, 255))
            img.save(img_path, format="JPEG", quality=85)

            caption = cat_data["captions"][i - 1]
            confidence = 0.45 if cat_name == "blurry" else 0.94

            metadata_list.append({
                "id": image_id,
                "filename": filename,
                "file_path": img_path,
                "subject": cat_data["subject"],
                "category": cat_data["category"],
                "attributes": cat_data["attrs"],
                "caption": caption,
                "confidence": confidence,
                "flagged_for_review": confidence < 0.70,
            })

    # Save corpus metadata
    corpus_file = os.path.join(CURRENT_DIR, "data", "corpus_metadata.json")
    with open(corpus_file, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2)

    print(f"Generated {len(metadata_list)} images in {IMAGES_DIR}")
    print(f"Saved corpus metadata to {corpus_file}")

    # Build Labeled Eval Dataset
    eval_dataset = [
        {
            "post_id": "post_01",
            "title": "Winter Habits of the Red Fox",
            "content": "Red foxes (Vulpes vulpes) adapt remarkably well to cold northern climates, using their bushy tails to stay warm and hunting small mammals under deep snow.",
            "expected_image_id": "fox_01",
            "expected_subject": "red fox",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_02",
            "title": "Apex Hunters: Timber Wolf Pack Dynamics",
            "content": "Gray wolves (Canis lupus) rely on strict pack hierarchies and collaborative hunting strategies to bring down large ungulates across vast territories.",
            "expected_image_id": "wolf_01",
            "expected_subject": "gray wolf",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_03",
            "title": "Why Golden Retrievers Make Loving Family Pets",
            "content": "With their gentle temperament and eagerness to please, domestic golden retriever dogs are one of the most beloved companion breeds worldwide.",
            "expected_image_id": "dog_01",
            "expected_subject": "golden retriever",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_04",
            "title": "Grizzly Bears and the Salmon Run",
            "content": "Coastal grizzly bears (Ursus arctos) gather along Alaskan rivers each summer to gorge on spawning salmon ahead of winter hibernation.",
            "expected_image_id": "bear_01",
            "expected_subject": "grizzly bear",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_05",
            "title": "White-Tailed Deer in North American Woodlands",
            "content": "White-tailed deer are agile herbivores that browse forest meadows and signal danger to their herd by flashing the bright white underside of their tails.",
            "expected_image_id": "deer_01",
            "expected_subject": "white-tailed deer",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_06",
            "title": "Vulpes vulpes: The Biology of European Wild Foxes",
            "content": "Known scientifically as Vulpes vulpes, the wild red fox is a cunning nocturnal omnivore recognized for its copper-colored coat and white chest patch.",
            "expected_image_id": "fox_02",
            "expected_subject": "red fox",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_07",
            "title": "Wolf Reintroduction Programs in National Parks",
            "content": "The restoration of gray wolves in wilderness reserves has balanced deer and elk populations, triggering a trophic cascade that revitalized riverbanks.",
            "expected_image_id": "wolf_02",
            "expected_subject": "gray wolf",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_08",
            "title": "Active Exercise Routines for Domestic Dogs",
            "content": "Regular fetch games, leash walking, and mental enrichment keep energetic domestic retrievers healthy and prevent destructive behavior.",
            "expected_image_id": "dog_02",
            "expected_subject": "golden retriever",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_09",
            "title": "Brown Bears and Northern Alpine Habitat",
            "content": "Grizzly bears roam mountain slopes feeding on alpine vegetation, small rodents, and roots using their long curved claws.",
            "expected_image_id": "bear_02",
            "expected_subject": "grizzly bear",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_10",
            "title": "Antler Growth Cycles in Male Deer",
            "content": "Male white-tailed deer shed and regrow their bone antlers annually, powered by testosterone surges during the autumn mating rut.",
            "expected_image_id": "deer_02",
            "expected_subject": "white-tailed deer",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_11",
            "title": "Modern Enterprise Datacenter Architecture",
            "content": "High-density server racks and redundant fiber optics ensure 99.999% uptime for mission-critical cloud computing workloads.",
            "expected_image_id": "tech_01",
            "expected_subject": "cloud datacenter",
            "expected_decision": "ACCEPTED",
        },
        {
            "post_id": "post_12",
            "title": "Abyssal Plain and Bioluminescent Deep Sea Organisms",
            "content": "At depths exceeding 4,000 meters, anglerfish and giant squids navigate total darkness using chemical luciferin light reactions.",
            "expected_image_id": None,  # Ground truth: NO SUITABLE IMAGE in our corpus
            "expected_subject": None,
            "expected_decision": "NO_CONFIDENT_MATCH",
        },
    ]

    eval_file = os.path.join(CURRENT_DIR, "data", "eval_dataset.json")
    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(eval_dataset, f, indent=2)

    print(f"Saved evaluation dataset ({len(eval_dataset)} test cases) to {eval_file}")


if __name__ == "__main__":
    build_corpus()
