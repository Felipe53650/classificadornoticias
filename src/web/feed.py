"""Conteúdo e consultas do feed local; exemplos nunca são gravados no banco."""
from math import ceil
from typing import Literal

from sqlalchemy import func, or_, select

from src.db.models import Article

FeedSource = Literal["all", "editorial", "demo"]
PAGE_SIZE = 7

# Textos fictícios escritos para demonstrar a navegação, independentes do dataset.
DEMO_STORIES = [
    ("cidade-mais-verde", "Cotidiano", "Uma cidade mais verde começa na esquina de casa",
     "Praças, jardins de chuva e espaços de convivência dão forma a uma proposta de bairro pensado para as pessoas.",
     "Nesta reportagem fictícia, moradores imaginam a transformação de um terreno vazio em uma praça. O projeto reúne caminhos acessíveis, árvores de sombra e bancos para quem deseja ficar um pouco mais.\n\nA proposta também inclui jardins de chuva, áreas com vegetação que ajudam a absorver a água. Oficinas abertas aproximam os moradores das escolhas sobre o espaço.\n\nO exemplo mostra como uma pauta de cotidiano pode conectar ambiente, mobilidade e convivência. Nenhuma obra ou iniciativa real está sendo anunciada.", "city"),
    ("tecnologia-no-dia-a-dia", "Tecnologia", "A tecnologia que cabe no dia a dia",
     "Um laboratório imaginário explora ferramentas simples para aproximar pessoas dos serviços digitais.",
     "Em um laboratório fictício, uma equipe testa interfaces para agendar serviços e encontrar informações públicas. O ponto de partida é ouvir quem encontra dificuldades ao usar essas ferramentas.\n\nOs protótipos incluem textos claros, contraste adequado e navegação pelo teclado. Cada rodada de testes ajuda a identificar etapas que podem ser simplificadas.\n\nEsta matéria é um exemplo editorial e não descreve um produto ou estudo real.", "tech"),
    ("cultura-ocupa-o-bairro", "Entretenimento", "Quando a cultura ocupa o bairro",
     "Música, cinema e encontros ao ar livre compõem a programação de um festival fictício.",
     "Um festival imaginário transforma espaços do bairro em pontos de encontro. Na programação de exemplo, há sessões de cinema, apresentações musicais e oficinas de criação.\n\nA ideia da matéria é mostrar como iniciativas culturais podem aproximar diferentes gerações. A acessibilidade aparece desde a escolha dos locais até a comunicação das atividades.\n\nNão há evento real, inscrições ou datas vinculados a este conteúdo demonstrativo.", "culture"),
    ("economia-das-pequenas-escolhas", "Economia", "As pequenas escolhas que movimentam a economia local",
     "Uma feira imaginária serve de cenário para conversar sobre comércio e consumo no bairro.",
     "Nesta simulação, comerciantes organizam uma feira para apresentar produtos e trocar experiências. O percurso da reportagem acompanha a preparação das bancas e a relação com os visitantes.\n\nO texto propõe perguntas sobre custos, circulação de mercadorias e planejamento. Não apresenta indicadores econômicos, preços reais ou recomendações de investimento.", "economy"),
    ("esporte-para-todos", "Esportes", "O primeiro passo para um esporte mais próximo de todos",
     "Um projeto fictício abre espaço para diferentes idades compartilharem a mesma quadra.",
     "Em um centro esportivo imaginário, atividades são organizadas para acolher iniciantes. A proposta valoriza a convivência e a adaptação das práticas ao grupo.\n\nA matéria acompanha uma manhã fictícia de jogos e conversas. O conteúdo foi criado para demonstrar a editoria de esportes e não anuncia vagas em um projeto real.", "sport"),
    ("ciencia-fora-do-laboratorio", "Ciência", "A curiosidade leva a ciência para fora do laboratório",
     "Uma exposição imaginária transforma perguntas do cotidiano em experiências de aprendizagem.",
     "Por que algumas sombras mudam de tamanho? Como a água percorre o solo? Em uma exposição fictícia, perguntas simples orientam atividades interativas.\n\nO roteiro imaginado incentiva visitantes a formular hipóteses e observar resultados. A reportagem é uma demonstração de conteúdo e não apresenta descobertas científicas ou dados de pesquisa.", "tech"),
    ("educacao-e-encontro", "Educação", "Uma biblioteca feita de livros e encontros",
     "Leitura compartilhada e oficinas dão vida a um espaço comunitário imaginário.",
     "Uma biblioteca fictícia organiza rodas de leitura e atividades de escrita. Além do empréstimo de livros, o espaço é pensado como um lugar para trocar histórias.\n\nNesta proposta de reportagem, a equipe conversa com personagens imaginários sobre os livros que marcaram sua formação. O texto não retrata uma instituição real.", "culture"),
    ("turismo-outro-ritmo", "Turismo", "Descobrir a cidade em outro ritmo",
     "Um passeio fictício a pé revela detalhes que costumam passar despercebidos.",
     "O roteiro imaginário começa em uma praça e segue por ruas com pequenos jardins e construções antigas. A narrativa convida a observar texturas, sons e espaços de convivência.\n\nEste exemplo não é um guia de viagem: os locais e o percurso foram criados para simular uma matéria de turismo no Pauta.", "city"),
]


def story_view(key, category, title, content, *, summary=None, theme="city", example=False, date=None):
    words = content.split()
    return {"key": key, "category": category, "title": title or "Notícia sem título",
            "content": content, "summary": summary or (" ".join(words[:32]) + ("…" if len(words) > 32 else "")),
            "theme": theme, "example": example, "date": date,
            "minutes": max(1, ceil(len(words) / 200))}


def demo_stories():
    return [story_view(f"demo-{slug}", category, title, content, summary=summary, theme=theme, example=True)
            for slug, category, title, summary, content, theme in DEMO_STORIES]


def article_view(article):
    return story_view(f"local-{article.id}", article.final_category, article.title, article.content,
                      theme={"Tecnologia": "tech", "Ciência": "tech", "Economia": "economy",
                             "Esportes": "sport", "Entretenimento": "culture"}.get(article.final_category, "city"),
                      date=article.created_at.strftime("%d/%m/%Y"))


def get_feed(session, *, category="", q="", source: FeedSource = "all", page=1):
    examples = demo_stories()
    categories = sorted(set(session.scalars(select(Article.final_category).distinct())) |
                        {item["category"] for item in examples})
    filters = []
    if category:
        filters.append(Article.final_category == category)
        examples = [item for item in examples if item["category"] == category]
    if q:
        filters.append(or_(Article.title.icontains(q, autoescape=True), Article.content.icontains(q, autoescape=True)))
        examples = [item for item in examples if q.lower() in (item["title"] + " " + item["content"]).lower()]
    if source == "editorial":
        examples = []
    local_total = session.scalar(select(func.count()).select_from(Article).where(*filters)) if source != "demo" else 0
    total = local_total + len(examples)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = min(page, pages)
    offset = (page - 1) * PAGE_SIZE
    items = []
    if offset < local_total:
        articles = session.scalars(select(Article).where(*filters).order_by(Article.id.desc()).offset(offset).limit(PAGE_SIZE))
        items = [article_view(article) for article in articles]
    demo_offset = max(0, offset - local_total)
    items.extend(examples[demo_offset:demo_offset + PAGE_SIZE - len(items)])
    return {"stories": items, "categories": categories, "total": total, "current_page": page, "pages": pages}
