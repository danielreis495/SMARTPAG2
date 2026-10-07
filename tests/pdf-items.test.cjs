const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(code); // Check syntax of the complete application script.
function setup() {
    const rows = [];
    const context = vm.createContext({document: {querySelectorAll: () => rows}});
    for (const name of ['valorEmCentavos', 'textoParaNumero', 'chaveLinhaJDE', 'pagamentoJaExiste']) {
        const start = code.indexOf(`        function ${name}(`);
        const end = code.indexOf('\n        function ', start + 1);
        vm.runInContext(code.slice(start, end), context);
    }
    return {rows, context};
}
test('Nilko: distinct JDE items preserve both cent lines; reimport is deduplicated', () => {
    const {rows, context: c} = setup();
    const values = ['11.967,30', ',01', ',01'];
    const items = ['003', '004', '005'];
    let cents = 0;
    for (let pass = 0; pass < 2; pass++) {
        values.forEach((value, i) => {
            const key = c.chaveLinhaJDE('973187', 'PV', '166768', '00001', items[i], '359989', '05/10/26', value);
            if (!c.pagamentoJaExiste(key)) {
                rows.push({getAttribute: () => key});
                cents += Math.round(c.textoParaNumero(value) * 100);
            }
        });
        assert.equal(rows.length, 3);
        assert.equal(cents, 1196732);
    }
    const saved = JSON.stringify(rows.map(row => ({chaveJDE: row.getAttribute()})));
    rows.splice(0, rows.length, ...JSON.parse(saved).map(row => ({getAttribute: () => row.chaveJDE})));
    assert.equal(c.pagamentoJaExiste(c.chaveLinhaJDE('973187', 'PV', '166768', '00001', '005', '359989', '05/10/26', '0,01')), true);
    assert.equal(c.pagamentoJaExiste(c.chaveLinhaJDE('973187', 'PV', '166768', '00002', '005', '359989', '05/10/26', '0,01')), false);
});
