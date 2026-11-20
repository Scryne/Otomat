window.PX = (function () {
  // Tek paylaşılan WebGL bağlamı: sahne başına bağlam açmak Chrome'un ~16 bağlam sınırına takılır.
  let gl = null, cv = null, pr = null, U = {};
  const onbellek = new Map();
  const VS = 'attribute vec2 p;varying vec2 uv;void main(){uv=p*0.5+0.5;uv.y=1.0-uv.y;gl_Position=vec4(p,0.,1.);}';
  const FS = `precision highp float;
uniform sampler2D im, de; uniform vec2 off; uniform float z, dz, bl, dof, od, asp; varying vec2 uv;
vec2 px(vec2 c){ vec2 q=c; for(int i=0;i<8;i++){ float d=texture2D(de,q).r; q=c+(off+(c-0.5)*dz)*(d-od); }
  return clamp(q,0.001,0.999); }
void main(){
  vec2 c=(uv-0.5)/z+0.5; vec2 q=px(c); vec4 col=texture2D(im,q);
  if(bl>0.0){
    float d=texture2D(de,q).r;
    float r=bl*(dof>0.5 ? clamp((od+0.2-d)*2.5,0.0,1.0) : 1.0);
    if(r>0.00005){ vec4 s=col; float n=1.0;
      for(int i=0;i<16;i++){ float a=float(i)*2.39996; float rr=r*sqrt((float(i)+0.5)/16.0);
        s+=texture2D(im,clamp(q+vec2(cos(a),sin(a)*asp)*rr,0.001,0.999)); n+=1.0; }
      col=s/n; }
  }
  gl_FragColor=col; }`;
  function kur() {
    cv = document.createElement('canvas');
    gl = cv.getContext('webgl', { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false });
    const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); return o; };
    pr = gl.createProgram();
    gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(pr); gl.useProgram(pr);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const lp = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 2, gl.FLOAT, false, 0, 0);
    for (const u of ['im', 'de', 'off', 'z', 'dz', 'bl', 'dof', 'od', 'asp']) U[u] = gl.getUniformLocation(pr, u);
    gl.uniform1i(U.im, 0); gl.uniform1i(U.de, 1);
  }
  function doku(img) {
    let t = onbellek.get(img.src);
    if (t) { onbellek.delete(img.src); onbellek.set(img.src, t); return t; }
    t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, img);
    onbellek.set(img.src, t);
    while (onbellek.size > 12) { const [k, v] = onbellek.entries().next().value; gl.deleteTexture(v); onbellek.delete(k); }
    return t;
  }
  function ciz(hedef, im, de, o, p) {
    if (!gl) kur();
    if (cv.width !== hedef.width || cv.height !== hedef.height) { cv.width = hedef.width; cv.height = hedef.height; }
    const ti = doku(im), td = doku(de);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, ti);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, td);
    const L = (a, b) => a + (b - a) * p;
    gl.uniform2f(U.off, L(o.x0, o.x1), L(o.y0, o.y1)); gl.uniform1f(U.z, L(o.z0, o.z1)); gl.uniform1f(U.dz, L(o.d0, o.d1));
    gl.uniform1f(U.bl, o.bl || 0); gl.uniform1f(U.dof, o.dof || 0); gl.uniform1f(U.od, o.od == null ? 0.4 : o.od);
    gl.uniform1f(U.asp, hedef.width / hedef.height);
    gl.viewport(0, 0, cv.width, cv.height); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    hedef.getContext('2d').drawImage(cv, 0, 0);
  }
  return { ciz };
})();
