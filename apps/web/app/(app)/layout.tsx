import "../../tokens.css";
import "./base.css";

import Colophon from "@/components/hoja/Colophon";
import Masthead from "@/components/hoja/Masthead";
import Sheet, { SheetBody } from "@/components/hoja/Sheet";

/**
 * Aplicación: cada página vive dentro de la hoja, entre la misma cabecera y
 * el mismo pie de créditos. El cajetín lo pone cada página, porque su
 * contenido depende de los datos que esa vista tenga a la vista.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <Sheet>
        <Masthead />
        <SheetBody>{children}</SheetBody>
        <Colophon />
      </Sheet>
    </>
  );
}
