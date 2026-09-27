import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

from app.config import Settings
from app.models import Query
from app.robot import Robot


async def run(query: Query):
    robot = Robot(Settings())
    await robot.start()
    try:
        return await robot.query(query)
    finally:
        await robot.close()


def main():
    parser = argparse.ArgumentParser(description="Consulta pessoas físicas no Portal da Transparência")
    parser.add_argument("termo", help="Nome, CPF ou NIS")
    parser.add_argument("--social", action="store_true", help="Filtrar beneficiários de programas sociais")
    parser.add_argument("--output", type=Path, help="Arquivo JSON; padrão: saída padrão")
    args = parser.parse_args()
    try:
        query = Query(termo=args.termo, beneficiario_programa_social=args.social)
    except ValidationError as exc:
        parser.error(str(exc))
    result = asyncio.run(run(query))
    payload = result.model_dump_json(indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    sys.exit(0 if result.status == "sucesso" else 2)


if __name__ == "__main__":
    main()
