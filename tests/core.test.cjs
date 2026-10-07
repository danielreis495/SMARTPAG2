const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),path=require('path');
const code=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function load(names,extras={}){
 const c=vm.createContext(extras);
 for(const name of names){const a=code.indexOf(`        function ${name}(`),ends=[code.indexOf('\n        function ',a+1),code.indexOf('\n        async function ',a+1)].filter(x=>x>=0);assert(a>=0);vm.runInContext(code.slice(a,Math.min(...ends)),c);}
 return c;
}
test('money preserves cents and rejects ambiguous/invalid inputs',()=>{
 const c=load(['valorEmCentavos','textoParaNumero','somarMoeda']);
 for(const [s,n]of [['1.500,00',150000],[',01',1],['0,01',1],['20,00-',-2000],['-20,00',-2000]])assert.equal(c.valorEmCentavos(s),n);
 for(const s of ['abc','1500.00','','1,2','-1,00-'])assert.throws(()=>c.valorEmCentavos(s));
 let total=0;for(let i=0;i<1000;i++)total=c.somarMoeda(total,.01);assert.equal(total,10);
});
test('second value edit updates the value, not the adjustment badge',()=>{
 const span={innerText:'100,00'},badge={innerText:'old adjustment'},attrs={'data-valor-original':'100,00'};
 const row={querySelector:s=>s==='.valor-texto'?span:badge,getAttribute:k=>attrs[k],setAttribute:(k,v)=>attrs[k]=v};
 const c=load(['valorEmCentavos','textoParaNumero','formatarMoeda','editarValor'],{prompt:()=> '120,00',alert(){},calcularTotais(){},informarOperacao(){}});
 c.editarValor({closest:()=>row,previousElementSibling:badge});assert.equal(span.innerText,'120,00');assert.equal(attrs['data-ajuste'],'tem ajuste de +R$ 20,00');
});
test('unknown reconciliation status and malformed monetary value are rejected',()=>{
 const c=load(['valorEmCentavos','validarConciliacao'],{BANCOS_NOMES:['itau']});
 const good={fornecedor:'Nilko',voucher:'166768',bancoSelecionado:'itau',status:'Pendente',valor:'11.967,32'};
 assert.equal(c.validarConciliacao([good]).length,1);
 assert.throws(()=>c.validarConciliacao([{...good,status:'unknown'}]));
 assert.throws(()=>c.validarConciliacao([{...good,valor:'abc'}]));assert.throws(()=>c.validarConciliacao({}));
});
test('unassigned group counted once in dashboard',()=>{
 const els={};const get=id=>els[id]??={value:'2026-10-05',classList:{add(){},remove(){}},closest(){return {classList:{add(){},remove(){}}}}};
 const row=value=>({getAttribute:()=> 'g',querySelector:s=>s==='.valor-texto'?{innerText:value}:s==='.select-banco'?{value:''}:s==='.select-classificacao'?{value:'Fornecedores'}:null,querySelectorAll:()=>Array.from({length:9},()=>({innerText:'Test'}))});
 const c=load(['escaparHTML','valorEmCentavos','textoParaNumero','somarMoeda','formatarMoeda','calcularTotais'],{document:{getElementById:get,querySelectorAll:()=>[row('100,00'),row('10,00-')]},BANCOS_NOMES:['itau'],BANCOS_LABEL:{itau:'Itaú'},salvarEstadoLocal(){},filtrarTabela(){}});
 c.calcularTotais();assert.equal(get('dashboard-total').innerText,'R$ 90,00');
});
test('markup from imported text is escaped',()=>{const c=load(['escaparHTML']);assert.equal(c.escaparHTML('<img src=x onerror="alert(1)">'),'&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')});
function parserContext(){
 const c=load(['valorEmCentavos','textoParaNumero','formatarMoeda','chaveLinhaJDE','interpretarPaginasJDE'],{TIPOS_DOC:['PV']});
 vm.runInContext(code.slice(code.indexOf('        const COLUNAS_JDE'),code.indexOf('        function processarPDF')),c);return c;
}
function pages(){
 const items=[];const word=(str,x,y)=>({str,transform:[1,0,0,1,x,y]});
 let y=500;
 for(const [item,value]of [['003','11.967,30'],['004',',01'],['005',',01']]){
  items.push(...[['973187 NILKO TECNOLOGIA LTDA',20],['PV',190],['166768',210],['00001',240],[item,263],['07/07/26',280],[value,330],['A',374],['973187 NILKO TECNOLOGIA LTDA',390],['359989',560],['05/10/26',750]].map(([str,x])=>word(str,x,y)));y-=12;
 }
 items.push(word('Total:',240,y),word('11.967,32',330,y));
 items.push(word('Valor Total a ser processado:',240,y-20),word('11.967,32',330,y-20));return [{items}];
}
test('parser checks every beneficiary and final total, preserving equal cent items',()=>{
 const c=parserContext(),p=pages(),r=c.interpretarPaginasJDE(p);
 assert.equal(r.pagamentos.length,3);assert.equal(r.totalCentavos,1196732);
 const broken=pages();broken[0].items=broken[0].items.filter(i=>i.transform[5]!==476);
 assert.throws(()=>c.interpretarPaginasJDE(broken),/Divergência/);
 const wrongFooter=pages();wrongFooter[0].items.at(-1).str='11.967,31';assert.throws(()=>c.interpretarPaginasJDE(wrongFooter),/Total geral divergente/);
 const missing=pages();missing[0].items.splice(-2);assert.throws(()=>c.interpretarPaginasJDE(missing),/incompleto/);
});
