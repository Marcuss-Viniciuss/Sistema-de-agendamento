# Sistema de agendamento simples para barbearia/clínica
# Projeto de portefólio - feito no terminal com sqlite3

import sqlite3

# Nome do ficheiro da base de dados (cria sozinho se não existir)
NOME_BD = "agendamentos.db"


def conectar():
    # Abre a ligação à base de dados
    # TODO: ver se há forma melhor de gerir as ligações
    return sqlite3.connect(NOME_BD)


def criar_tabela():
    # Cria a tabela se ainda não existir, assim não dá erro na primeira vez
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            servico TEXT NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL
        )
    """)
    conexao.commit()
    conexao.close()


def data_valida(data):
    # Verificação básica: tem de ter o formato DD/MM/AAAA
    # Só confere o tamanho e as barras, não vê se o dia existe mesmo
    # TODO: melhorar essa validação depois (ex: dia 45/13/2025 passa!)
    if len(data) != 10:
        return False
    if data[2] != "/" or data[5] != "/":
        return False
    # Confere se o resto são números
    if not (data[0:2].isdigit() and data[3:5].isdigit() and data[6:10].isdigit()):
        return False
    return True


def hora_valida(hora):
    # Verificação básica: formato HH:MM
    # TODO: não verifica se a hora é maior que 23, por exemplo
    if len(hora) != 5:
        return False
    if hora[2] != ":":
        return False
    if not (hora[0:2].isdigit() and hora[3:5].isdigit()):
        return False
    return True


def horario_ocupado(data, hora):
    # Vai à base de dados ver se já existe alguém marcado nesse dia e hora
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM agendamentos WHERE data = ? AND hora = ?",
        (data, hora)
    )
    resultado = cursor.fetchone()
    conexao.close()

    # Se encontrou alguma coisa, o horário está ocupado
    if resultado is not None:
        return True
    return False


def adicionar_agendamento():
    print("\n--- Adicionar Agendamento ---")

    # Aqui eu pego o nome do cliente
    cliente = input("Nome do cliente: ").strip()
    if cliente == "":
        print("O nome não pode ficar vazio!")
        return

    # Aqui o serviço (corte, barba, consulta, etc.)
    servico = input("Serviço (ex: corte, barba): ").strip()
    if servico == "":
        print("O serviço não pode ficar vazio!")
        return

    # Pego a data e confiro o formato
    data = input("Data (DD/MM/AAAA): ").strip()
    if not data_valida(data):
        print("Data inválida! Usa o formato DD/MM/AAAA, por exemplo 25/12/2025.")
        return

    # Pego a hora e confiro o formato
    hora = input("Hora (HH:MM): ").strip()
    if not hora_valida(hora):
        print("Hora inválida! Usa o formato HH:MM, por exemplo 14:30.")
        return

    # Antes de guardar, vejo se o horário já está ocupado
    if horario_ocupado(data, hora):
        print("Esse horário já está ocupado! Escolhe outro.")
        return

    # Se chegou aqui, está tudo certo e guardo na base de dados
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO agendamentos (cliente, servico, data, hora) VALUES (?, ?, ?, ?)",
        (cliente, servico, data, hora)
    )
    conexao.commit()
    conexao.close()

    print("Agendamento guardado com sucesso!")


def ver_agendamentos():
    print("\n--- Lista de Agendamentos ---")

    conexao = conectar()
    cursor = conexao.cursor()
    # TODO: ordenar por data de verdade. Como a data é texto (DD/MM/AAAA),
    # a ordenação fica meio estranha entre meses/anos diferentes
    cursor.execute("SELECT id, cliente, servico, data, hora FROM agendamentos ORDER BY data, hora")
    agendamentos = cursor.fetchall()
    conexao.close()

    # Se a lista vier vazia, avisa e sai
    if len(agendamentos) == 0:
        print("Ainda não há agendamentos.")
        return

    # Mostra cada agendamento, um por linha
    for ag in agendamentos:
        print(f"[{ag[0]}] {ag[3]} às {ag[4]} - {ag[1]} ({ag[2]})")


def cancelar_agendamento():
    print("\n--- Cancelar Agendamento ---")

    # Mostro a lista primeiro para a pessoa saber qual ID escolher
    ver_agendamentos()

    id_texto = input("\nDigita o ID do agendamento a cancelar (ou Enter para voltar): ").strip()

    # Se a pessoa não escreveu nada, volta ao menu
    if id_texto == "":
        return

    # Garante que o que foi digitado é mesmo um número
    if not id_texto.isdigit():
        print("O ID tem de ser um número!")
        return

    id_agendamento = int(id_texto)

    conexao = conectar()
    cursor = conexao.cursor()

    # Primeiro vejo se esse ID existe
    cursor.execute("SELECT id FROM agendamentos WHERE id = ?", (id_agendamento,))
    existe = cursor.fetchone()

    if existe is None:
        print("Não encontrei nenhum agendamento com esse ID.")
        conexao.close()
        return

    # Se existe, apaga
    cursor.execute("DELETE FROM agendamentos WHERE id = ?", (id_agendamento,))
    conexao.commit()
    conexao.close()

    print("Agendamento cancelado!")


def mostrar_menu():
    # Só imprime as opções do menu
    print("\n===== AGENDAMENTOS =====")
    print("1 - Adicionar Agendamento")
    print("2 - Ver Agendamentos")
    print("3 - Cancelar Agendamento")
    print("4 - Sair")


def main():
    # Garante que a tabela existe antes de tudo
    criar_tabela()

    # Loop principal: repete o menu até a pessoa escolher sair
    while True:
        mostrar_menu()
        opcao = input("Escolhe uma opção: ").strip()

        if opcao == "1":
            adicionar_agendamento()
        elif opcao == "2":
            ver_agendamentos()
        elif opcao == "3":
            cancelar_agendamento()
        elif opcao == "4":
            print("Até à próxima!")
            break
        else:
            print("Opção inválida, tenta outra vez.")


if __name__ == "__main__":
    main()
