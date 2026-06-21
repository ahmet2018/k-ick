import discord
from discord.ext import commands
import asyncio
import os
from keep_alive import keep_alive
from kick_logic import KickViewerBot, BotSettings, Colors
import logging

# Discord Bot Kurulumu
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global bot değişkeni
kick_bot_instance = None

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    await bot.change_presence(activity=discord.Game(name="Kick Viewer Bot"))

@bot.command()
async def baslat(ctx, kanal_adi: str, izleyici_sayisi: int):
    global kick_bot_instance
    
    if kick_bot_instance:
        await ctx.send("❌ Bot zaten çalışıyor! Durdurmak için `!durdur` yazın.")
        return

    await ctx.send(f"🚀 **{kanal_adi}** kanalı için **{izleyici_sayisi}** izleyici botu başlatılıyor...")
    
    # Ayarları oluştur
    settings = BotSettings(
        channel=kanal_adi.lower(),
        viewer_goal=izleyici_sayisi,
        auto_start=True,
        verbose=True
    )
    
    kick_bot_instance = KickViewerBot(settings)
    
    try:
        # Botu asenkron olarak arka planda çalıştır
        asyncio.create_task(kick_bot_instance.run())
        await ctx.send(f"✅ Bot başarıyla başlatıldı. İstatistikleri görmek için `!durum` yazabilirsiniz.")
    except Exception as e:
        await ctx.send(f"❌ Bir hata oluştu: {e}")
        kick_bot_instance = None

@bot.command()
async def durum(ctx):
    global kick_bot_instance
    
    if not kick_bot_instance:
        await ctx.send("❌ Şu an çalışan bir bot yok.")
        return
    
    stats = await kick_bot_instance.stats.get_stats()
    
    embed = discord.Embed(title="📊 Kick Bot İstatistikleri", color=discord.Color.green())
    embed.add_field(name="📺 Kanal", value=kick_bot_instance.settings.channel, inline=True)
    embed.add_field(name="⏱️ Çalışma Süresi", value=stats.uptime_str, inline=True)
    embed.add_field(name="🔗 Aktif Bağlantı", value=f"{stats.active_connections}/{len(kick_bot_instance.workers)}", inline=True)
    embed.add_field(name="✅ Başarılı", value=stats.successful_connections, inline=True)
    embed.add_field(name="❌ Başarısız", value=stats.failed_connections, inline=True)
    embed.add_field(name="📈 Başarı Oranı", value=f"%{stats.success_rate:.1f}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def durdur(ctx):
    global kick_bot_instance
    
    if not kick_bot_instance:
        await ctx.send("❌ Zaten çalışan bir bot yok.")
        return
    
    await ctx.send("🛑 Bot durduruluyor...")
    await kick_bot_instance.stop()
    kick_bot_instance = None
    await ctx.send("✅ Bot başarıyla durduruldu.")

# Render için Keep Alive başlat
keep_alive()

# Botu çalıştır (Token çevresel değişkenden alınmalı)
TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ HATA: DISCORD_TOKEN bulunamadı! Lütfen çevresel değişkenlere ekleyin.")
