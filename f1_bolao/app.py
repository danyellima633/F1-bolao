import streamlit as st,sqlite3,pandas as pd

pilotos=["Lando Norris","Oscar Piastri","Max Verstappen","Isack Hadjar","George Russell","Kimi Antonelli","Charles Leclerc","Lewis Hamilton","Fernando Alonso","Lance Stroll","Carlos Sainz","Alex Albon","Pierre Gasly","Franco Colapinto","Esteban Ocon","Oliver Bearman","Nico Hulkenberg","Gabriel Bortoleto","Liam Lawson","Arvid Lindblad","Sergio Perez","Valtteri Bottas"]
gps=["Monaco","Barcelona-Catalunya","Áustria","Grã-Bretanha","Bélgica","Hungria","Holanda","Itália","Espanha","Azerbaijão","Singapura","Estados Unidos","México","Brasil","Las Vegas","Catar","Abu Dhabi"]
pts={1:1,2:2,3:4,4:6,5:8,6:10,7:12,8:15,9:18,10:25}
users={"Danyel":{"senha":"senha","admin":True},"Rogério":{"senha":"ceni","admin":False}}

con=sqlite3.connect("f1_bolao.db")
cur=con.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS palpites(gp TEXT,pessoa TEXT,posicao INTEGER,piloto TEXT,PRIMARY KEY(gp,pessoa,posicao));
CREATE TABLE IF NOT EXISTS extras(gp TEXT,pessoa TEXT,pole TEXT,melhor_volta TEXT,PRIMARY KEY(gp,pessoa));
CREATE TABLE IF NOT EXISTS resultados(gp TEXT,posicao INTEGER,piloto TEXT,PRIMARY KEY(gp,posicao));
CREATE TABLE IF NOT EXISTS resultados_extras(gp TEXT PRIMARY KEY,pole TEXT,melhor_volta TEXT);
""")
con.commit()

st.title("Bolão F1")

if "user" not in st.session_state:
    nome=st.selectbox("Usuário",list(users))
    senha=st.text_input("Senha",type="password")
    if st.button("Entrar") and senha==users[nome]["senha"]:
        st.session_state.user=nome
        st.session_state.admin=users[nome]["admin"]
        st.rerun()
    st.stop()

st.sidebar.write(f"Usuário: {st.session_state.user}")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

abas=["Palpites","Ranking"]+["Resultado real"]*st.session_state.admin
aba=st.sidebar.radio("Tela",abas)
gp=st.sidebar.selectbox("GP",gps)

if aba=="Palpites":
    pessoa=st.session_state.user
    st.subheader(f"Palpites — GP de {gp}")
    old=pd.read_sql("SELECT posicao,piloto FROM palpites WHERE gp=? AND pessoa=?",con,params=(gp,pessoa))
    olde=pd.read_sql("SELECT pole,melhor_volta FROM extras WHERE gp=? AND pessoa=?",con,params=(gp,pessoa,))
    old=dict(zip(old.posicao,old.piloto)) if len(old) else {}
    escolhas={}
    for i in range(1,11):
        escolhas[i]=st.selectbox(f"{i}º lugar",pilotos,index=pilotos.index(old[i]) if i in old and old[i] in pilotos else 0,key=f"p{i}")
    pole0=olde.pole.iloc[0] if len(olde) and olde.pole.iloc[0] in pilotos else pilotos[0]
    mv0=olde.melhor_volta.iloc[0] if len(olde) and olde.melhor_volta.iloc[0] in pilotos else pilotos[0]
    pole=st.selectbox("Pole position",pilotos,index=pilotos.index(pole0),key="pole")
    mv=st.selectbox("Melhor volta",pilotos,index=pilotos.index(mv0),key="mv")
    if len(set(escolhas.values()))<10: st.warning("Há piloto repetido no top 10.")
    if st.button("Salvar palpites"):
        for i,p in escolhas.items(): cur.execute("INSERT OR REPLACE INTO palpites VALUES(?,?,?,?)",(gp,pessoa,i,p))
        cur.execute("INSERT OR REPLACE INTO extras VALUES(?,?,?,?)",(gp,pessoa,pole,mv))
        con.commit()
        st.success("Palpites salvos.")

elif aba=="Resultado real":
    st.subheader(f"Resultado real — GP de {gp}")
    old=pd.read_sql("SELECT posicao,piloto FROM resultados WHERE gp=?",con,params=(gp,))
    olde=pd.read_sql("SELECT pole,melhor_volta FROM resultados_extras WHERE gp=?",con,params=(gp,))
    old=dict(zip(old.posicao,old.piloto)) if len(old) else {}
    res={}
    for i in range(1,11):
        res[i]=st.selectbox(f"{i}º lugar real",pilotos,index=pilotos.index(old[i]) if i in old and old[i] in pilotos else 0,key=f"r{i}")
    pole0=olde.pole.iloc[0] if len(olde) and olde.pole.iloc[0] in pilotos else pilotos[0]
    mv0=olde.melhor_volta.iloc[0] if len(olde) and olde.melhor_volta.iloc[0] in pilotos else pilotos[0]
    pole=st.selectbox("Pole real",pilotos,index=pilotos.index(pole0),key="rpole")
    mv=st.selectbox("Melhor volta real",pilotos,index=pilotos.index(mv0),key="rmv")
    if len(set(res.values()))<10: st.warning("Há piloto repetido no top 10 real.")
    if st.button("Salvar resultado real"):
        for i,p in res.items(): cur.execute("INSERT OR REPLACE INTO resultados VALUES(?,?,?)",(gp,i,p))
        cur.execute("INSERT OR REPLACE INTO resultados_extras VALUES(?,?,?)",(gp,pole,mv))
        con.commit()
        st.success("Resultado real salvo.")

else:
    p=pd.read_sql("SELECT * FROM palpites",con)
    r=pd.read_sql("SELECT * FROM resultados",con)
    e=pd.read_sql("SELECT * FROM extras",con)
    re=pd.read_sql("SELECT * FROM resultados_extras",con)
    if p.empty or r.empty:
        st.write("Ainda não há palpites e resultados suficientes.")
    else:
        x=p.merge(r,on=["gp","posicao"],suffixes=("_palpite","_real"))
        x["categoria"]=x.posicao.astype(str)+"º lugar"
        x["pontos"]=x.apply(lambda z: pts[z.posicao] if z.piloto_palpite==z.piloto_real else 0,axis=1)
        y=e.merge(re,on="gp",suffixes=("_palpite","_real"))
        pole=y.assign(categoria="Pole",pontos=3*(y.pole_palpite==y.pole_real))[["gp","pessoa","categoria","pontos"]]
        mv=y.assign(categoria="Melhor volta",pontos=1*(y.melhor_volta_palpite==y.melhor_volta_real))[["gp","pessoa","categoria","pontos"]]
        base=pd.concat([x[["gp","pessoa","categoria","pontos"]],pole,mv])
        resumo=base.pivot_table(index="pessoa",columns="gp",values="pontos",aggfunc="sum",fill_value=0).reindex(columns=gps,fill_value=0).astype(int)
        resumo["Total"]=resumo.sum(axis=1)
        st.subheader("Ranking geral")
        st.dataframe(resumo.sort_values("Total",ascending=False),use_container_width=True)

        cats=[f"{i}º lugar" for i in range(1,11)]+["Pole","Melhor volta"]
        pessoas=list(users)

        for gp0 in gps:
            if gp0 not in set(pd.concat([p.gp,r.gp,e.gp,re.gp],ignore_index=True)): continue
            st.subheader(gp0)
            real_pos=r[r.gp==gp0].set_index("posicao").piloto.to_dict()
            real_extra=re[re.gp==gp0]
            real_pole=real_extra.pole.iloc[0] if len(real_extra) else ""
            real_mv=real_extra.melhor_volta.iloc[0] if len(real_extra) else ""
            for pessoa in pessoas:
                pal_pos=p[(p.gp==gp0)&(p.pessoa==pessoa)].set_index("posicao").piloto.to_dict()
                pal_extra=e[(e.gp==gp0)&(e.pessoa==pessoa)]
                pal_pole=pal_extra.pole.iloc[0] if len(pal_extra) else ""
                pal_mv=pal_extra.melhor_volta.iloc[0] if len(pal_extra) else ""
                dados=[]
                for i in range(1,11): dados.append([f"{i}º lugar",pal_pos.get(i,""),real_pos.get(i,"")])
                dados+=[["Pole",pal_pole,real_pole],["Melhor volta",pal_mv,real_mv]]
                st.markdown(f"**{pessoa}**")
                st.dataframe(pd.DataFrame(dados,columns=["Categoria","Palpite","Resultado real"]).set_index("Categoria"),use_container_width=True)
