import os
import sys
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.sql_db import init_db, SessionLocal, Startup, FundingRound, NewsArticle
from backend.database.qdrant_db import init_qdrant, get_qdrant_client, COLLECTION_NAME
from backend.database.graph_db import get_graph_engine
from backend.raptor.tree import build_raptor_tree
from backend.ingestion.scraper import extract_entities_and_relationships

load_dotenv()

# Seed Profiles
STARTUP_PROFILES = [
    {
        "name": "OpenAI",
        "website": "https://openai.com",
        "market": "Generative AI & LLMs",
        "description": "OpenAI is an AI research and deployment company. Its mission is to ensure that artificial general intelligence benefits all of humanity.",
        "tech_stack": "Python, PyTorch, Kubernetes, Azure, Triton",
        "logo_url": "https://logo.clearbit.com/openai.com",
        "documents": [
            "OpenAI was founded in late 2015 by Sam Altman, Elon Musk, Greg Brockman, Ilya Sutskever, and Wojciech Zaremba, with a $1 billion funding commitment from tech leaders. Musk resigned from the board in 2018 to avoid potential conflicts with Tesla's self-driving initiatives.",
            "In 2019, OpenAI transitioned from a non-profit organization to a 'capped-profit' corporate structure, allowing it to raise venture capital and issue equity. This transition paved the way for Microsoft's initial $1 billion investment in OpenAI, which grew to a cumulative $13 billion partnership.",
            "OpenAI launched ChatGPT in November 2022, kicking off a global generative AI boom. ChatGPT reached 100 million active monthly users in two months, making it the fastest-growing consumer application in history. ChatGPT uses OpenAI's GPT-3.5 and GPT-4 model families.",
            "OpenAI is competing directly with Anthropic, Cohere, Google, and Meta in the LLM space. OpenAI provides enterprise APIs, ChatGPT Plus subscription models, and is actively building AI agents code-named 'Operator' that can take actions on computers directly.",
            "OpenAI has faced governance challenges, notably in November 2023 when the non-profit board briefly fired CEO Sam Altman over communication issues. After employee outcry and investor pressure, Altman returned as CEO, and Microsoft secured a non-voting observer seat on the board."
        ],
        "funding": [
            {"round_type": "Partnership", "amount": 1000000000.0, "investors": "Microsoft", "date": "2019-07-22"},
            {"round_type": "Corporate Venture", "amount": 10000000000.0, "investors": "Microsoft, Thrive Capital", "date": "2023-01-23"},
            {"round_type": "Tender Offer", "amount": 6600000000.0, "investors": "Altimeter Capital, Thrive Capital, Khosla Ventures, SoftBank", "date": "2024-10-02"}
        ]
    },
    {
        "name": "Anthropic",
        "website": "https://anthropic.com",
        "market": "Generative AI & LLMs",
        "description": "Anthropic is an AI safety and research company that builds reliable, beneficial, and controllable AI systems. It is the creator of the Claude models.",
        "tech_stack": "Python, PyTorch, AWS, Google Cloud, JAX",
        "logo_url": "https://logo.clearbit.com/anthropic.com",
        "documents": [
            "Anthropic was founded in 2021 by Dario Amodei (former OpenAI VP of Research) and Daniela Amodei (former OpenAI VP of Safety), alongside other OpenAI researchers. They split from OpenAI due to concerns regarding the commercialization speed and safety practices of AI development.",
            "Anthropic pioneered 'Constitutional AI', an alignment training method designed to make AI systems helpful, honest, and harmless without human feedback loops. Claude is trained to follow a set of principles derived from declarations of human rights and safety guidelines.",
            "In 2023, Amazon announced it would invest up to $4 billion in Anthropic, becoming its primary cloud provider for training models on AWS Trainium chips. Google followed with a $2 billion investment commitment, using Google Cloud TPU hardware.",
            "Anthropic released Claude 3.5 Sonnet in June 2024, showing superior performance in coding, reasoning, and visual analysis compared to GPT-4o. In October 2024, they released 'Computer Use' API, enabling the Claude agent to control mouse pointers and keyboard inputs.",
            "Anthropic competes directly with OpenAI in frontier models, serving enterprises like Slack, Notion, and Bridgewater Associates. Anthropic operates as a Public Benefit Corporation (PBC) governed by a Long-Term Benefit Trust to ensure safety alignment."
        ],
        "funding": [
            {"round_type": "Series A", "amount": 124000000.0, "investors": "Jaan Tallinn, Dustin Moskovitz", "date": "2021-05-28"},
            {"round_type": "Series B", "amount": 580000000.0, "investors": "Sam Bankman-Fried, Caroline Ellison", "date": "2022-04-29"},
            {"round_type": "Corporate Venture", "amount": 4000000000.0, "investors": "Amazon", "date": "2023-09-25"},
            {"round_type": "Corporate Venture", "amount": 2000000000.0, "investors": "Google", "date": "2023-10-27"}
        ]
    },
    {
        "name": "Cohere",
        "website": "https://cohere.com",
        "market": "Enterprise Generative AI",
        "description": "Cohere builds AI technology for enterprise applications, providing natural language processing models optimized for search, retrieval, and generation.",
        "tech_stack": "Python, PyTorch, Oracle Cloud, Google Cloud",
        "logo_url": "https://logo.clearbit.com/cohere.com",
        "documents": [
            "Cohere was founded in 2019 by Aidan Gomez, Ivan Zhang, and Nick Frosst. Gomez is well-known as a co-author of the seminal 2017 Google research paper 'Attention Is All You Need', which introduced the Transformer architecture that underpins all modern LLMs.",
            "Unlike OpenAI and Anthropic, Cohere does not focus on consumer applications like chatbots. Instead, it positions itself as cloud-agnostic and enterprise-focused, specializing in Retrieval-Augmented Generation (RAG) and semantic search models.",
            "Cohere introduced Command R and Command R+ in early 2024. These models are optimized for multi-step agentic tasks, tool use, and 10+ languages, and they are deployable in secure enterprise virtual private clouds (VPC).",
            "In June 2024, Cohere raised $450 million in a Series D funding round at a $5.5 billion valuation, led by NVIDIA, Oracle, Salesforce Ventures, and Canadian pension funds. The capital will fund enterprise customer acquisitions and compute resource expansions.",
            "Cohere partners heavily with Oracle, integrating its LLM technology into Oracle's cloud infrastructure database services, and with McKinsey & Company to build custom enterprise chatbot agents."
        ],
        "funding": [
            {"round_type": "Series A", "amount": 40000000.0, "investors": "Index Ventures, Tiger Global", "date": "2021-09-07"},
            {"round_type": "Series B", "amount": 125000000.0, "investors": "Tiger Global, Section 32", "date": "2022-02-17"},
            {"round_type": "Series C", "amount": 270000000.0, "investors": "Inovia Capital, NVIDIA, Oracle", "date": "2023-06-08"},
            {"round_type": "Series D", "amount": 450000000.0, "investors": "NVIDIA, Oracle, Salesforce Ventures", "date": "2024-06-18"}
        ]
    },
    {
        "name": "Qdrant",
        "website": "https://qdrant.tech",
        "market": "Vector Databases & Search",
        "description": "Qdrant is an open-source vector database and similarity search engine written in Rust, optimized for RAG and AI applications.",
        "tech_stack": "Rust, Actix-web, gRPC, Docker, Kubernetes",
        "logo_url": "https://logo.clearbit.com/qdrant.tech",
        "documents": [
            "Qdrant was founded in Berlin in 2021 by Andre Zayarni and Javid Mammadov. They built the engine in Rust to handle high-performance similarity search over millions of high-dimensional vectors with sub-millisecond latencies.",
            "Qdrant enables developers to perform filtered vector search, which combines vector distance comparisons with structured SQL-like payload filters (such as dates, markets, or startup names). This is highly useful for context-aware RAG pipelines.",
            "In January 2024, Qdrant raised a $28 million Series A funding round led by Spark Capital, with participation from unusual ventures. The funds are earmarked to build out Qdrant Cloud, its managed vector hosting platform.",
            "Qdrant competes in the fast-growing vector infrastructure market against Pinecone, Weaviate, Milvus, and pgvector. Its advantages include being written in memory-safe Rust, lightweight resource footprint, and native support for payload filtering.",
            "With the emergence of hierarchical RAG systems like RAPTOR, Qdrant is widely used to store multiple layers of documents, summaries, and parent-child vector points to perform multi-hop cognitive retrieval."
        ],
        "funding": [
            {"round_type": "Seed", "amount": 2300000.0, "investors": "Unusual Ventures, IBB Ventures", "date": "2022-04-12"},
            {"round_type": "Series A", "amount": 28000000.0, "investors": "Spark Capital, Unusual Ventures", "date": "2024-01-23"}
        ]
    },
    {
        "name": "Cursor",
        "website": "https://cursor.com",
        "market": "AI Coding Assistants",
        "description": "Cursor (built by Anysphere) is an AI-first code editor fork of VS Code, enabling deep codebase-level auto-completions, chat, and automated edits.",
        "tech_stack": "TypeScript, Electron, Rust, C++, Next.js",
        "logo_url": "https://logo.clearbit.com/cursor.com",
        "documents": [
            "Cursor was built by Anysphere, a startup founded by MIT graduates Arvid Lunnemark, Michael Truell, Sualeh Asif, and Aman Sanger in 2022. It is developed as a direct fork of VS Code to offer integrated, keyboard-friendly AI editing.",
            "Cursor features 'Composer' and 'Tab Autocomplete' which index the entire local directory structure, building codebase embeddings. It enables the editor to write multi-file edits, refactor methods, and find reference bugs automatically.",
            "In August 2024, Anysphere raised over $60 million in Series A funding at a $400 million valuation, led by Andreessen Horowitz, with participation from OpenAI Startup Fund and notable angel investors like Jeff Dean.",
            "Cursor competes directly with GitHub Copilot, Windsurf (Codeium), Cline, and Aider. Developers praise Cursor for its superior codebase context matching and speed compared to traditional chat extensions.",
            "Anysphere licenses model access from OpenAI and Anthropic, using custom high-throughput proxy setups to stream completions to users with sub-100ms latency."
        ],
        "funding": [
            {"round_type": "Seed", "amount": 8000000.0, "investors": "OpenAI Startup Fund, Lachy Groom", "date": "2023-10-12"},
            {"round_type": "Series A", "amount": 60000000.0, "investors": "Andreessen Horowitz, Thrive Capital", "date": "2024-08-22"}
        ]
    },
    {
        "name": "Windsurf",
        "website": "https://codeium.com/windsurf",
        "market": "AI Coding Assistants",
        "description": "Windsurf is an agentic IDE built by Codeium, featuring an interactive agent loop that works side-by-side with developers.",
        "tech_stack": "TypeScript, C++, Python, Go, WASM",
        "logo_url": "https://logo.clearbit.com/codeium.com",
        "documents": [
            "Windsurf was launched in late 2024 by Codeium (originally Exafunction), a company founded in 2021 by Varun Mohan and Douglas Chen. Codeium has a background in building AI acceleration infrastructure before pivoting to developer tools.",
            "Windsurf introduces the concept of the 'Flow State' and 'cascade' agent technology. The AI agent can run terminal commands, write code, run compilers, and fix errors in a continuous autonomous loop, with the developer acting as an orchestrator.",
            "Codeium raised a $150 million Series C funding round in August 2024 at a $1.25 billion valuation, led by General Catalyst, with participation from Kleiner Perkins and Greenoaks. This funding directly powered the launch of the Windsurf IDE.",
            "Windsurf competes directly with Cursor, VS Code, and Aider. Unlike Cursor, which historically relied on external API calls, Codeium runs its own proprietary developer LLM infrastructure in cloud clusters to lower operational costs.",
            "Windsurf supports multi-turn conversations and features a dual mode: Chat (asking queries) and Cascade (giving the agent command of the file workspace to execute tasks)."
        ],
        "funding": [
            {"round_type": "Series A", "amount": 25000000.0, "investors": "Greenoaks, Kleiner Perkins", "date": "2022-06-16"},
            {"round_type": "Series B", "amount": 65000000.0, "investors": "Kleiner Perkins, General Catalyst", "date": "2024-02-05"},
            {"round_type": "Series C", "amount": 150000000.0, "investors": "General Catalyst, Greenoaks", "date": "2024-08-29"}
        ]
    }
]

def seed_database():
    print("Starting database seeding...")
    
    # 1. Initialize Relational DB
    init_db()
    db: Session = SessionLocal()
    
    # Clear relational tables
    db.query(NewsArticle).delete()
    db.query(FundingRound).delete()
    db.query(Startup).delete()
    db.commit()
    print("Cleared existing relational data.")
    
    # 2. Initialize Qdrant Collection
    init_qdrant()
    q_client = get_qdrant_client()
    try:
        q_client.delete_collection(COLLECTION_NAME)
        print("Cleared existing vector data.")
    except Exception as e:
        print(f"Vector delete collection warning: {e}")
    init_qdrant()
    
    # 3. Initialize Graph DB
    graph_engine = get_graph_engine()
    graph_engine.clear_all()
    print("Cleared existing graph data.")
    
    total_rounds = 0
    total_articles = 0
    total_nodes = 0
    total_edges = 0
    
    for profile in STARTUP_PROFILES:
        name = profile["name"]
        print(f"\nProcessing Startup: {name}...")
        
        # 3.1 RAPTOR pipeline (VectorDB) & Level 3 summary
        print(f"-> Building RAPTOR tree for {name}...")
        raptor_summary = build_raptor_tree(name, profile["documents"])
        
        # Calculate funding total
        funding_total = sum(f["amount"] for f in profile["funding"])
        
        # 3.2 SQL insertion
        startup = Startup(
            name=name,
            website=profile["website"],
            market=profile["market"],
            description=profile["description"],
            tech_stack=profile["tech_stack"],
            funding_total=funding_total,
            logo_url=profile["logo_url"],
            raptor_summary=raptor_summary
        )
        db.add(startup)
        db.commit()
        
        # Add funding rounds
        for r in profile["funding"]:
            round_obj = FundingRound(
                startup_name=name,
                round_type=r["round_type"],
                amount=r["amount"],
                investors=r["investors"],
                date=r["date"]
            )
            db.add(round_obj)
            total_rounds += 1
            
        # Add news/documents as articles
        for idx, doc in enumerate(profile["documents"]):
            art = NewsArticle(
                startup_name=name,
                title=f"Source Document {idx+1} for {name}",
                content=doc,
                url=profile["website"],
                source="Internal Research",
                date="2024-10-01"
            )
            db.add(art)
            total_articles += 1
            
        db.commit()
        
        # 3.3 Graph construction (extract relations via mock / rule-based helper)
        print(f"-> Extracting Graph nodes and edges for {name}...")
        # Since we have documents, we combine them into a single string for parsing
        full_doc_text = " ".join(profile["documents"])
        graph_extracted = extract_entities_and_relationships(full_doc_text, name)
        
        # Save nodes
        for node in graph_extracted.get("nodes", []):
            nid = node["id"]
            label = node["label"]
            props = node.get("properties", {})
            graph_engine.add_node(nid, label, props)
            total_nodes += 1
            
        # Save edges
        for edge in graph_extracted.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            rel_type = edge["type"]
            props = edge.get("properties", {})
            graph_engine.add_relationship(source, target, rel_type, props)
            total_edges += 1
            
    db.close()
    
    # 4. Global Graph Relationships setup (Cross relationships not auto-linked by profiles)
    print("\nSetting up cross-startup competitive and investor edges...")
    # Add some additional manual edges to enrich the graph structure for queries
    cross_relationships = [
        ("OpenAI", "Anthropic", "COMPETES_WITH"),
        ("OpenAI", "Cohere", "COMPETES_WITH"),
        ("Anthropic", "Cohere", "COMPETES_WITH"),
        ("Cursor", "Windsurf", "COMPETES_WITH"),
        ("Qdrant", "Vector Databases", "USES_TECH"),
        ("Cursor", "AI Coding Assistants", "USES_TECH"),
        ("Windsurf", "AI Coding Assistants", "USES_TECH"),
        ("Microsoft", "OpenAI", "PARTNERED_WITH"),
        ("Amazon", "Anthropic", "PARTNERED_WITH"),
        ("Google", "Anthropic", "PARTNERED_WITH"),
        ("Thrive Capital", "OpenAI", "FUNDED_BY"),
        ("Thrive Capital", "Cursor", "FUNDED_BY"),
        ("Spark Capital", "Qdrant", "FUNDED_BY"),
        ("General Catalyst", "Windsurf", "FUNDED_BY")
    ]
    
    for src, tgt, rtype in cross_relationships:
        graph_engine.add_relationship(src, tgt, rtype)
        total_edges += 1
        
    print("Seeding process completed!")
    print(f"Summary: Seeded {len(STARTUP_PROFILES)} startups, {total_rounds} funding rounds, {total_articles} articles.")
    print(f"Graph stats: Extracted {total_nodes} nodes, added {total_edges} relations.")
    
    return {
        "startups_seeded": len(STARTUP_PROFILES),
        "funding_rounds_seeded": total_rounds,
        "articles_seeded": total_articles,
        "nodes_added": total_nodes,
        "edges_added": total_edges
    }

if __name__ == "__main__":
    seed_database()
