export interface SiteInput { readonly id: string; readonly origin: string; readonly trailingSlash: 'always' | 'never'; }
export interface Site extends SiteInput {}
export interface DocumentInput {
  readonly id: string; readonly kind: string; readonly status: string; readonly access: string;
  readonly path: string; readonly title: string; readonly summary: string;
  readonly canonicalUrl?: string; readonly availableAt?: string;
  readonly sourceMetadata?: unknown; readonly [key: string]: unknown;
}
export interface ValidatedMetadata extends DocumentInput { readonly canonicalUrl: string; }
export interface SchemaInput {
  readonly kinds: readonly string[]; readonly statuses: readonly string[]; readonly accessLevels: readonly string[];
  readonly publishedStatus: string; readonly publicAccess: string;
  readonly validateSource: (metadata: Readonly<ValidatedMetadata>) => boolean;
}
declare const metadataSchemaBrand: unique symbol;
export interface MetadataSchema extends Omit<SchemaInput, 'validateSource'> { readonly [metadataSchemaBrand]: true; }
export interface PublicationSelection { readonly publishedAt?: string; readonly updatedAt?: string; }
export interface PublicEntry {
  readonly id: string; readonly kind: string; readonly path: string; readonly title: string;
  readonly summary: string; readonly canonicalUrl: string; readonly availableAt: string;
  readonly publishedAt?: string; readonly updatedAt?: string;
}
export interface Inventory { readonly evaluatedAt: number; readonly entries: readonly PublicEntry[]; }
export interface ProjectionOptions {
  readonly schema: MetadataSchema; readonly now: number;
  readonly selectPublication: (metadata: Readonly<ValidatedMetadata>, evaluatedAt: number) => PublicationSelection | null;
}
export declare function utcInstant(value: string): string;
export declare function defineSite(input: SiteInput): Readonly<Site>;
export declare function canonicalPath(site: SiteInput, path: string): string;
export declare function defineMetadataSchema(input: SchemaInput): Readonly<MetadataSchema>;
export declare function projectPublicInventory(site: SiteInput, documents: readonly DocumentInput[], options: ProjectionOptions): Readonly<Inventory>;
