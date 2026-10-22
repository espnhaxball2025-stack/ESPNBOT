import discord
from discord import app_commands
import json
import os
from threading import Thread
from flask import Flask

# Servidor Flask falso para que Render no tire timeout por falta de puertos web
app = Flask('')

@app.route('/')
def home():
    return "EspnHaxball Bot está activo 24/7 en la nube."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ID correcta y oficial de tu servidor de Discord
GUILD_ID = discord.Object(id=1378906986682257408)

DATA_FILE = "haxball_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"clubs": {}, "tournaments": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"clubs": {}, "tournaments": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class HaxballBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)
        print(f"Bot conectado como {self.user}. Comandos sincronizados correctamente.")

bot = HaxballBot()

# ==========================================
# MODAL PARA EDITAR PLANTILLA
# ==========================================
class EditarPlantillaModal(discord.ui.Modal):
    def __init__(self, club_name: str):
        super().__init__(title=f"Editar Plantilla: {club_name[:20]}")
        self.club_name = club_name
        
        self.nueva_plantilla = discord.ui.TextInput(
            label="Nueva Plantilla de Jugadores",
            placeholder="Jugador1, Jugador2, Jugador3...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )
        self.add_item(self.nueva_plantilla)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        club = data["clubs"].get(self.club_name)

        if not club:
            await interaction.response.send_message("El club seleccionado ya no existe.", ephemeral=True)
            return

        club["plantilla"] = self.nueva_plantilla.value.strip()
        save_data(data)

        embed = discord.Embed(
            title="Plantilla Actualizada",
            description=f"La plantilla del club **{self.club_name}** ha sido modificada con éxito.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Nueva Plantilla", value=club["plantilla"], inline=False)
        embed.set_footer(text="EspnHaxball Mercadodepases System")

        await interaction.response.send_message(embed=embed, ephemeral=False)

# ==========================================
# VISTA PARA SELECCIONAR QUÉ CLUB EDITAR
# ==========================================
class EditClubSelectView(discord.ui.View):
    def __init__(self, clubs):
        super().__init__()
        options = [discord.SelectOption(label=name[:100], description=f"Editar plantilla de {name}") for name in clubs.keys()]
        self.add_item(EditClubSelect(options))

class EditClubSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Selecciona el club a modificar...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        club_name = self.values[0]
        await interaction.response.send_modal(EditarPlantillaModal(club_name))

# ==========================================
# MODAL PARA EL COMANDO /anuncio
# ==========================================
class AnuncioModal(discord.ui.Modal, title="Crear Anuncio Oficial - EspnHaxball"):
    titulo = discord.ui.TextInput(
        label="Título del Anuncio",
        placeholder="Ej: 🚨 COMUNICADO OFICIAL | ESPNHAXBALL",
        required=True,
        max_length=150
    )
    contenido = discord.ui.TextInput(
        label="Mensaje (puedes usar **negrita**, etc.)",
        placeholder="Escribe el cuerpo del comunicado aquí...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.titulo.value,
            description=self.contenido.value,
            color=discord.Color.from_rgb(255, 69, 0)
        )
        embed.set_footer(text="EspnHaxball Official System • Publicado por " + interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("¡Anuncio publicado correctamente en el canal!", ephemeral=True)

# ==========================================
# MODAL PARA /registrar-club
# ==========================================
class ClubModal(discord.ui.Modal, title="Registro Oficial de Club - EspnHaxball"):
    nombre = discord.ui.TextInput(
        label="Nombre Oficial del Club",
        placeholder="Ej: Racing Club Haxball",
        required=True,
        max_length=100
    )
    logo_url = discord.ui.TextInput(
        label="Logo o Escudo (URL válida)",
        placeholder="https://ejemplo.com/escudo.png",
        required=True
    )
    presidente = discord.ui.TextInput(
        label="Presidente (Nombre o mención)",
        placeholder="@Usuario o Juan Pérez",
        required=True,
        max_length=100
    )
    plantilla = discord.ui.TextInput(
        label="Plantilla de Jugadores",
        placeholder="Jugador1, Jugador2, Jugador3...",
        style=discord.TextStyle.paragraph,
        required=True
    )
    fundacion = discord.ui.TextInput(
        label="Fecha de Fundación (Opcional)",
        placeholder="Ej: 15/04/2023",
        required=False,
        max_length=30
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        club_key = self.nombre.value.strip().lower()

        if club_key in [k.lower() for k in data["clubs"].keys()]:
            await interaction.response.send_message(
                "Error: Ya existe un club registrado con ese nombre.", ephemeral=True
            )
            return

        data["clubs"][self.nombre.value.strip()] = {
            "nombre": self.nombre.value.strip(),
            "logo": self.logo_url.value.strip(),
            "presidente": self.presidente.value.strip(),
            "plantilla": self.plantilla.value.strip(),
            "titulos": 0,
            "fundacion": self.fundacion.value.strip() if self.fundacion.value else "No especificada",
            "torneos": []
        }
        save_data(data)

        embed = discord.Embed(
            title="Nuevo Club Oficial Registrado",
            description=f"El club **{self.nombre.value.strip()}** ha sido registrado exitosamente.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=self.logo_url.value.strip())
        embed.add_field(name="Presidente", value=self.presidente.value.strip(), inline=True)
        embed.add_field(name="Fundación", value=self.fundacion.value.strip() or "No especificada", inline=True)
        embed.add_field(name="Plantilla", value=self.plantilla.value.strip(), inline=False)
        embed.add_field(name="Títulos Iniciales", value="0", inline=True)
        embed.set_footer(text="EspnHaxball Official System")

        await interaction.response.send_message(embed=embed)

# ==========================================
# VISTAS Y MENÚS DESPLEGABLES
# ==========================================
class ClubSelectView(discord.ui.View):
    def __init__(self, clubs):
        super().__init__()
        options = []
        for name in clubs.keys():
            label = name[:100]
            options.append(discord.SelectOption(label=label, description=f"Ver ficha de {name}"))
        self.add_item(ClubSelect(options))

class ClubSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Seleccione un club para ver su ficha...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_data()
        club_name = self.values[0]
        club = data["clubs"].get(club_name)

        if not club:
            await interaction.response.send_message("No se encontró el club especificado.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Ficha Oficial: {club['nombre']}",
            color=discord.Color.blue()
        )
        if club.get("logo"):
            embed.set_thumbnail(url=club["logo"])
        
        embed.add_field(name="Presidente", value=club["presidente"], inline=True)
        embed.add_field(name="Fundación", value=club["fundacion"], inline=True)
        embed.add_field(name="Títulos", value=str(club["titulos"]), inline=True)
        embed.add_field(name="Plantilla Oficial", value=club["plantilla"], inline=False)
        
        torneos_str = ", ".join(club["torneos"]) if club["torneos"] else "Ninguno asignado"
        embed.add_field(name="Torneos Participantes", value=torneos_str, inline=False)
        embed.set_footer(text="EspnHaxball Club Management")

        await interaction.response.edit_message(embed=embed, view=None)

class AddTorneoView(discord.ui.View):
    def __init__(self, clubs, tournaments):
        super().__init__()
        self.selected_club = None
        self.selected_tournament = None

        club_options = [discord.SelectOption(label=name[:100]) for name in clubs.keys()]
        self.club_select = discord.ui.Select(placeholder="Seleccione el club...", options=club_options, row=0)
        self.club_select.callback = self.club_callback
        self.add_item(self.club_select)

        tourney_options = [discord.SelectOption(label=t[:100]) for t in tournaments]
        self.tourney_select = discord.ui.Select(placeholder="Seleccione el torneo...", options=tourney_options, row=1)
        self.tourney_select.callback = self.tourney_callback
        self.add_item(self.tourney_select)

    async def club_callback(self, interaction: discord.Interaction):
        self.selected_club = self.club_select.values[0]
        await interaction.response.defer()

    async def tourney_callback(self, interaction: discord.Interaction):
        self.selected_tournament = self.tourney_select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Confirmar Asignación", style=discord.ButtonStyle.success, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_club or not self.selected_tournament:
            await interaction.response.send_message("Debe seleccionar un club y un torneo antes de confirmar.", ephemeral=True)
            return

        data = load_data()
        club = data["clubs"].get(self.selected_club)

        if not club:
            await interaction.response.send_message("El club seleccionado ya no existe.", ephemeral=True)
            return

        if self.selected_tournament in club["torneos"]:
            await interaction.response.send_message(f"El club **{self.selected_club}** ya se encuentra registrado en el torneo **{self.selected_tournament}**.", ephemeral=True)
            return

        club["torneos"].append(self.selected_tournament)
        save_data(data)

        embed = discord.Embed(
            title="Torneo Asignado Exitosamente",
            description=f"El club **{self.selected_club}** ha sido inscripto en el torneo **{self.selected_tournament}**.",
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=embed, view=None)

# ==========================================
# COMANDOS DE SLASH
# ==========================================

@bot.tree.command(name="anuncio", description="Crea un comunicado oficial con formato para el canal")
@app_commands.checks.has_permissions(administrator=True)
async def anuncio(interaction: discord.Interaction):
    await interaction.response.send_modal(AnuncioModal())

@bot.tree.command(name="editar-plantilla", description="Modifica la plantilla de jugadores de un club oficial")
@app_commands.checks.has_permissions(administrator=True)
async def editar_plantilla(interaction: discord.Interaction):
    data = load_data()
    if not data["clubs"]:
        await interaction.response.send_message("No hay clubes registrados para editar.", ephemeral=True)
        return
    
    view = EditClubSelectView(data["clubs"])
    await interaction.response.send_message("Seleccione el club al que desea cambiarle la plantilla:", view=view, ephemeral=True)

@bot.tree.command(name="mercado-de-pases", description="Consulta el mercado de pases actual")
async def mercado_de_pases(interaction: discord.Interaction):
    await interaction.response.send_message("Mercado de pases abierto.", ephemeral=False)

@bot.tree.command(name="registrar-club", description="Registra oficialmente un club de HaxBall")
@app_commands.checks.has_permissions(administrator=True)
async def registrar_club(interaction: discord.Interaction):
    await interaction.response.send_modal(ClubModal())

@bot.tree.command(name="club", description="Consulta la información completa de un club registrado")
async def club(interaction: discord.Interaction):
    data = load_data()
    if not data["clubs"]:
        await interaction.response.send_message("No hay clubes registrados actualmente.", ephemeral=True)
        return
    
    view = ClubSelectView(data["clubs"])
    await interaction.response.send_message("Seleccione el club que desea consultar:", view=view, ephemeral=True)

@bot.tree.command(name="registrar-torneo", description="Registra un nuevo torneo oficial")
@app_commands.checks.has_permissions(administrator=True)
async def registrar_torneo(interaction: discord.Interaction, nombre_torneo: str):
    data = load_data()
    nombre_limpio = nombre_torneo.strip()

    if nombre_limpio in data["tournaments"]:
        await interaction.response.send_message(f"El torneo **{nombre_limpio}** ya existe en el sistema.", ephemeral=True)
        return

    data["tournaments"].append(nombre_limpio)
    save_data(data)

    await interaction.response.send_message(f"Torneo **{nombre_limpio}** registrado correctamente.", ephemeral=False)

@bot.tree.command(name="add-torneo", description="Asigna un torneo registrado a un club oficial")
@app_commands.checks.has_permissions(administrator=True)
async def add_torneo(interaction: discord.Interaction):
    data = load_data()
    if not data["clubs"]:
        await interaction.response.send_message("No hay clubes registrados.", ephemeral=True)
        return
    if not data["tournaments"]:
        await interaction.response.send_message("No hay torneos registrados.", ephemeral=True)
        return

    view = AddTorneoView(data["clubs"], data["tournaments"])
    await interaction.response.send_message("Seleccione el club y el torneo a vincular:", view=view, ephemeral=True)

@anuncio.error
@editar_plantilla.error
@registrar_club.error
@registrar_torneo.error
@add_torneo.error
async def admin_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("No cuenta con los permisos de administrador necesarios para ejecutar este comando.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Se ha producido un error: {error}", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: No se ha configurado la variable de entorno DISCORD_TOKEN.")
    else:
        bot.run(TOKEN)
