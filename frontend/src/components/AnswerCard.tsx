import type { Answer } from '../types'
import { splitIntoBlocks } from '../lib/text'
import { Highlighted } from './Highlighted'
import { BookIcon, ScrollIcon, SealIcon } from './icons'
import { LegalNotice } from './LegalNotice'

const ACCENTS = ['gold', 'blue', 'seal'] as const

type Accent = (typeof ACCENTS)[number]

function accentAt(index: number): Accent {
  return ACCENTS[index % ACCENTS.length]
}

interface AnswerCardProps {
  answer: Answer
}

export function AnswerCard({ answer }: AnswerCardProps) {
  const blocks = splitIntoBlocks(answer.en_clair)

  return (
    <section className="answer" aria-label="Explication">
      <header className="answer__head">
        <span className="answer__seal" aria-hidden="true">
          <SealIcon size={17} />
        </span>
        <h2>Explication</h2>
        <span className="answer__tag">Lexi · En clair</span>
      </header>

      {answer.extrait && (
        <figure className="answer__quote">
          <figcaption>
            <ScrollIcon size={14} />
            Extrait du document
          </figcaption>
          <blockquote>
            <Highlighted text={answer.extrait} />
          </blockquote>
        </figure>
      )}

      <div className="answer__explain">
        {blocks.map((block, index) => (
          <p
            className={`answer__sentence answer__sentence--${accentAt(index)}`}
            key={`${index}-${block.slice(0, 24)}`}
            style={{ animationDelay: `${index * 90}ms` }}
          >
            <Highlighted text={block} />
          </p>
        ))}
      </div>

      {answer.a_retenir.length > 0 && (
        <div className="answer__retain">
          <h3>
            <BookIcon size={15} />À retenir
          </h3>
          <ul>
            {answer.a_retenir.map((point, index) => (
              <li
                className={`answer__point answer__point--${accentAt(index)}`}
                key={point}
                style={{ animationDelay: `${index * 90 + 120}ms` }}
              >
                <span className="answer__point-text">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <LegalNotice />
    </section>
  )
}
